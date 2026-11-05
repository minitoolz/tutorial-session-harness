--[[
html2latex.lua — keep inline HTML alive when the target is LaTeX/PDF, and
make LaTeX math environments render in the HTML preview.

Pandoc's markdown reader splits raw HTML into fragments, e.g.
  RawBlock "<table>", RawBlock "<tr>", Plain [...], RawBlock "</tr>", ...
The LaTeX writer silently drops every fragment. This filter gathers each
element from its opening tag to its matching closing tag, serialises the
slice back to HTML (inner markdown/math included), and re-reads it with
pandoc's HTML reader so it becomes a real table / image / sub / sup / ...

It makes `$$ ... $$` the only display-math syntax a page needs:
  `$$ ... \label{eq:x} $$`            -> \begin{equation} ... \end{equation} (numbered)
  `$$ \begin{align} ... \end{align} $$` -> the align environment itself
  `$$ ... $$` without a label          -> unnumbered, as pandoc writes it

It renders mermaid diagrams (```mermaid or ```{.mermaid #fig:id caption="..." width="80%"})
to an image with mermaid-cli: PDF for LaTeX, SVG for HTML. `tutor build` passes the
mmdc path in TUTOR_MMDC, whether to pass --pdfFit in TUTOR_MMDC_PDFFIT (from the mmdc
version) and the cache folder in TUTOR_MERMAID_DIR.

It renders every `>` blockquote as a side note: a `tutornote` box in LaTeX (defined in each
style) and a `<div class="note">` in the HTML preview.

It also implements code includes:
  ```{.python include="codes/softmax.py" lines="3-20"}
  ```
]]

local is_latex = FORMAT:match("latex") ~= nil or FORMAT:match("pdf") ~= nil
local is_html = FORMAT:match("html") ~= nil

local VOID = {
  area = true, base = true, br = true, col = true, embed = true, hr = true,
  img = true, input = true, link = true, meta = true, source = true,
  track = true, wbr = true,
}

local UNSUPPORTED = {
  iframe = true, script = true, video = true, audio = true, canvas = true,
  style = true, object = true, embed = true, svg = true, form = true,
  button = true, input = true, select = true, textarea = true,
}

local function warn(msg)
  io.stderr:write("[html2latex] WARNING: " .. msg .. "\n")
end

-- Parse the first tag of a raw HTML string.
-- Returns kind ("open" | "close" | "self" | nil), tag name.
local function tag_info(text)
  local s = text:match("^%s*(.-)%s*$")
  if s:match("^<!%-%-") then return "comment", nil end
  local close = s:match("^</%s*([%w%-]+)")
  if close then return "close", close:lower() end
  local name = s:match("^<%s*([%w%-]+)")
  if not name then return nil, nil end
  name = name:lower()
  if VOID[name] or s:match("/>%s*$") then return "self", name end
  -- complete element on one fragment, e.g. "<sub>2</sub>" or "<iframe ...></iframe>"
  if s:match("</%s*" .. name .. "%s*>%s*$") then return "self", name end
  return "open", name
end

local function placeholder_inline(name)
  warn("<" .. name .. "> cannot be rendered in PDF; replaced with a placeholder")
  return pandoc.Emph({ pandoc.Str("[" .. name .. " omitted in PDF]") })
end

local function placeholder_block(name)
  warn("<" .. name .. "> cannot be rendered in PDF; replaced with a placeholder")
  return pandoc.RawBlock("latex",
    "\\begin{center}\\fbox{\\emph{[" .. name .. " omitted in PDF]}}\\end{center}")
end

-- Math and raw TeX (\eqref{..}, \ref{..}, ...) survive the HTML round-trip as
-- opaque placeholders; the HTML writer would otherwise drop raw TeX silently.
local math_store = {}
local MARK = "TUTORMATH"

local function is_tex(raw)
  return raw.format == "tex" or raw.format == "latex"
end

local function stash(inline)
  math_store[#math_store + 1] = inline
  return pandoc.Str(MARK .. #math_store .. "Z")
end

local function protect_math(el)
  return el:walk({
    Math = stash,
    RawInline = function(r)
      if is_tex(r) then return stash(r) end
    end,
    RawBlock = function(r)
      if is_tex(r) then return pandoc.Plain({ stash(pandoc.RawInline("latex", r.text)) }) end
    end,
  })
end

local function restore_str(s)
  local text = s.text
  if not text:find(MARK, 1, true) then return nil end
  local out = pandoc.Inlines({})
  local pos = 1
  while true do
    local a, b, n = text:find(MARK .. "(%d+)Z", pos)
    if not a then break end
    if a > pos then out:insert(pandoc.Str(text:sub(pos, a - 1))) end
    out:insert(math_store[tonumber(n)])
    pos = b + 1
  end
  if pos <= #text then out:insert(pandoc.Str(text:sub(pos))) end
  return out
end

local function blocks_to_html(blocks)
  local doc = protect_math(pandoc.Pandoc(blocks))
  local html = pandoc.write(doc, "html")
  -- <details><summary>T</summary>…</details>: show the summary as a bold lead-in
  html = html:gsub("<summary>(.-)</summary>", "<p><strong>%1</strong></p>")
  return html
end

local function html_to_blocks(html)
  local doc = pandoc.read(html, "html")
  doc = doc:walk({ Str = restore_str })
  return doc.blocks
end

-- Find the index of the fragment that closes `name`, starting at i.
local function find_close(list, i, name, raw_type)
  local depth = 0
  for j = i, #list do
    local el = list[j]
    if el.t == raw_type and el.format == "html" then
      local kind, n = tag_info(el.text)
      if n == name then
        if kind == "open" then depth = depth + 1
        elseif kind == "close" then
          depth = depth - 1
          if depth == 0 then return j end
        end
      end
    end
  end
  return nil
end

------------------------------------------------------------------------
-- Blocks
------------------------------------------------------------------------
local function fix_blocks(blocks)
  if not is_latex then return nil end
  local out = pandoc.Blocks({})
  local i = 1
  while i <= #blocks do
    local b = blocks[i]
    if b.t == "RawBlock" and b.format == "html" then
      local kind, name = tag_info(b.text)
      if kind == "comment" then
        i = i + 1
      elseif name and UNSUPPORTED[name] then
        local j = (kind == "open") and find_close(blocks, i, name, "RawBlock") or i
        out:insert(placeholder_block(name))
        i = (j or i) + 1
      elseif kind == "open" then
        local j = find_close(blocks, i, name, "RawBlock")
        if not j then
          warn("unclosed <" .. name .. ">; dropped")
          i = i + 1
        else
          local slice = pandoc.Blocks({})
          for k = i, j do slice:insert(blocks[k]) end
          out:extend(html_to_blocks(blocks_to_html(slice)))
          i = j + 1
        end
      elseif kind == "self" then
        out:extend(html_to_blocks(b.text))
        i = i + 1
      else
        i = i + 1 -- stray closing tag
      end
    else
      out:insert(b)
      i = i + 1
    end
  end
  return out
end

------------------------------------------------------------------------
-- Inlines
------------------------------------------------------------------------
local function html_inline(html)
  local blocks = html_to_blocks(html)
  if #blocks == 0 then return {} end
  if #blocks == 1 and (blocks[1].t == "Para" or blocks[1].t == "Plain") then
    return blocks[1].content
  end
  -- e.g. <img> becomes a Figure: keep the image itself inline
  local inl = pandoc.Inlines({})
  for _, blk in ipairs(blocks) do
    blk:walk({ Image = function(img) inl:insert(img) end })
  end
  if #inl > 0 then return inl end
  return pandoc.utils.blocks_to_inlines(blocks)
end

local fix_inlines
fix_inlines = function(inlines)
  local out = pandoc.Inlines({})
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    if is_latex and el.t == "RawInline" and el.format == "html" then
      local kind, name = tag_info(el.text)
      if kind == "comment" then
        i = i + 1
      elseif name and UNSUPPORTED[name] then
        local j = (kind == "open") and find_close(inlines, i, name, "RawInline") or i
        out:insert(placeholder_inline(name))
        i = (j or i) + 1
      elseif kind == "open" then
        local j = find_close(inlines, i, name, "RawInline")
        if not j then
          i = i + 1
        elseif name == "dfn" then
          -- a defined term: bold, like **term** (the other form the review accepts)
          local inner = pandoc.Inlines({})
          for k = i + 1, j - 1 do inner:insert(inlines[k]) end
          out:insert(pandoc.Strong(fix_inlines(inner)))
          i = j + 1
        else
          local slice = pandoc.Inlines({})
          for k = i, j do slice:insert(inlines[k]) end
          out:extend(html_inline(blocks_to_html({ pandoc.Plain(slice) })))
          i = j + 1
        end
      elseif kind == "self" then
        if name == "br" then
          out:insert(pandoc.LineBreak())
        else
          out:extend(html_inline(el.text))
        end
        i = i + 1
      else
        i = i + 1
      end
    elseif is_html and el.t == "RawInline" and el.format == "tex" then
      -- HTML preview: turn LaTeX math environments / refs into something visible
      local env_body = el.text:match("^\\begin{(%a+%*?)}")
      if env_body then
        local tex = el.text:gsub("\\label{[^}]*}", "")
        out:insert(pandoc.Math("DisplayMath", tex))
      else
        local ref = el.text:match("^\\eqref{([^}]*)}") or el.text:match("^\\ref{([^}]*)}")
        if ref then
          out:insert(pandoc.Str("(" .. ref .. ")"))
        else
          out:insert(el)
        end
      end
      i = i + 1
    else
      out:insert(el)
      i = i + 1
    end
  end
  return out
end

------------------------------------------------------------------------
-- Display math written as $$ ... $$
------------------------------------------------------------------------
-- Environments that make their own display (and numbers) in LaTeX; they can't
-- sit inside the \[ ... \] that pandoc writes for $$ ... $$.
local TOP_ENVS = {
  equation = true, align = true, gather = true, multline = true,
  flalign = true, alignat = true, eqnarray = true,
}

local function display_math(m)
  if m.mathtype ~= "DisplayMath" then return nil end
  local tex = m.text:match("^%s*(.-)%s*$")
  local env = tex:match("^\\begin{(%a+)%*?}")
  local has_label = tex:find("\\label{") ~= nil
  if is_latex then
    -- $$ \begin{align} ... \end{align} $$: emit the environment itself
    if env and TOP_ENVS[env] and tex:match("\\end{" .. env .. "%*?}$") then
      return pandoc.RawInline("latex", tex)
    end
    -- $$ ... \label{eq:x} $$: a numbered equation
    if has_label then
      return pandoc.RawInline("latex", "\\begin{equation}\n" .. tex .. "\n\\end{equation}")
    end
    return nil
  end
  -- other formats (HTML preview): drop labels so they don't render as text
  if has_label then
    return pandoc.Math("DisplayMath", (m.text:gsub("\\label{[^}]*}", "")))
  end
  return nil
end

------------------------------------------------------------------------
-- Mermaid diagrams
------------------------------------------------------------------------
local MMDC = os.getenv("TUTOR_MMDC") or ""
-- `tutor build` sets this from `mmdc --version`: mermaid-cli 12 fits PDFs by default and
-- rejects --pdfFit, older versions need it.
local MMDC_PDFFIT = (os.getenv("TUTOR_MMDC_PDFFIT") or "1") == "1"
local MERMAID_DIR = os.getenv("TUTOR_MERMAID_DIR") or "build/mermaid"

local function file_exists(path)
  local fh = io.open(path, "r")
  if fh then fh:close() return true end
  return false
end

local function mermaid(cb)
  if not cb.classes:includes("mermaid") then return nil end
  if MMDC == "" then
    warn("mermaid diagram left as code: mermaid-cli (mmdc) not configured")
    return nil
  end
  local ext = is_html and "svg" or "pdf"
  local base = MERMAID_DIR .. "/" .. pandoc.utils.sha1(cb.text)
  local out = base .. "." .. ext
  if not file_exists(out) then
    local fh = assert(io.open(base .. ".mmd", "w"))
    fh:write(cb.text)
    fh:close()
    local args = { "-i", base .. ".mmd", "-o", out, "-q",
                   "-b", is_html and "transparent" or "white" }
    if ext == "pdf" and MMDC_PDFFIT then args[#args + 1] = "--pdfFit" end
    local ok, err = pcall(pandoc.pipe, MMDC, args, "")
    if not ok or not file_exists(out) then
      error("mermaid diagram failed to render (check its syntax):\n" .. cb.text ..
            "\n" .. tostring(err))
    end
  end
  local img_attr = {}
  if cb.attributes["width"] then img_attr.width = cb.attributes["width"] end
  local img = pandoc.Image({}, out, "", pandoc.Attr("", {}, img_attr))
  local caption = cb.attributes["caption"]
  if caption or cb.identifier ~= "" then
    local cap = caption and pandoc.read(caption, "markdown").blocks or {}
    return pandoc.Figure({ pandoc.Plain({ img }) }, cap, pandoc.Attr(cb.identifier))
  end
  return pandoc.Para({ img })
end

------------------------------------------------------------------------
-- Code includes
------------------------------------------------------------------------
local function code_include(cb)
  local path = cb.attributes["include"]
  if not path then return nil end
  local fh = io.open(path, "r")
  if not fh then
    warn("include not found: " .. path)
    return nil
  end
  local text = fh:read("a")
  fh:close()
  local range = cb.attributes["lines"]
  if range then
    local a, b = range:match("^(%d+)%-(%d+)$")
    a, b = tonumber(a), tonumber(b)
    if a and b then
      local kept, n = {}, 0
      for line in (text .. "\n"):gmatch("(.-)\n") do
        n = n + 1
        if n >= a and n <= b then kept[#kept + 1] = line end
      end
      text = table.concat(kept, "\n")
    end
  end
  cb.attributes["include"] = nil
  cb.attributes["lines"] = nil
  cb.text = text:gsub("\n$", "")
  return cb
end

-- `>` blockquotes are side notes (the reader may skip them), drawn as a box.
local function note(bq)
  if is_latex then
    local out = { pandoc.RawBlock("latex", "\\begin{tutornote}") }
    for _, b in ipairs(bq.content) do out[#out + 1] = b end
    out[#out + 1] = pandoc.RawBlock("latex", "\\end{tutornote}")
    return out
  elseif is_html then
    return pandoc.Div(bq.content, pandoc.Attr("", { "note" }))
  end
end

return {
  { CodeBlock = function(cb) return mermaid(cb) or code_include(cb) end },
  { Inlines = fix_inlines },
  { Blocks = fix_blocks },
  { Math = display_math }, -- after fix_blocks, so math restored from HTML is covered too
  { BlockQuote = note },
}

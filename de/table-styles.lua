local function has_class(el, class)
  for _, c in ipairs(el.classes) do
    if c == class then
      return true
    end
  end
  return false
end


local function replace_once(text, old, new)

  local i, j = text:find(old, 1, true)

  if not i then
    return text
  end

  return text:sub(1, i - 1)
      .. new
      .. text:sub(j + 1)
end


local function get_style(el)

  if has_class(el, "zebra") then
    return {
      head  = "zebrahead",
      light = "zebralight",
      dark  = "zebradark"
    }
  end

  if has_class(el, "zebra_blue") then
    return {
      head  = "zebrabluehead",
      light = "zebrabluelight",
      dark  = "zebrabluedark"
    }
  end

  return nil
end


-- ---------------------------------------------------------
-- Remove Pandoc's outer @{} from longtable
-- ---------------------------------------------------------

local function fix_outer_table_padding(tex)

  -- Beginning:
  -- \begin{longtable}[]{@{}...
  -- becomes
  -- \begin{longtable}[]{...

  tex = tex:gsub(
    "\\begin{longtable}%[%]%{@%{%}",
    "\\begin{longtable}[]{",
    1
  )

  -- End of column definition:
  -- ...@{}}
  -- becomes
  -- ...}

  local begin_pos = tex:find(
    "\\begin{longtable}",
    1,
    true
  )

  if begin_pos then

    local end_pos = tex:find(
      "@{}}",
      begin_pos,
      true
    )

    if end_pos then
      tex =
        tex:sub(1, end_pos - 1) ..
        "}" ..
        tex:sub(end_pos + 4)
    end

  end

  return tex
end


-- ---------------------------------------------------------
-- Color body rows
-- ---------------------------------------------------------

local function color_body_rows(tex, lightcolor, darkcolor)

  local marker = "\\endlastfoot"

  local _, marker_end = tex:find(
    marker,
    1,
    true
  )

  if marker_end == nil then
    return tex
  end


  local table_end = tex:find(
    "\\end{longtable}",
    marker_end + 1,
    true
  )

  if table_end == nil then
    return tex
  end


  local before = tex:sub(
    1,
    marker_end
  )

  local body = tex:sub(
    marker_end + 1,
    table_end - 1
  )

  local after = tex:sub(
    table_end
  )


  body = body:gsub(
    "^\r?\n",
    ""
  )


  local n = 0


  body = body:gsub(
    "(.-\\\\%s*\n)",
    function(row)

      n = n + 1

      local color

      if n % 2 == 1 then
        color = lightcolor
      else
        color = darkcolor
      end


      return
        "\\rowcolor{" ..
        color ..
        "}\n" ..
        row ..
        "\\arrayrulecolor{tableline}\n" ..
        "\\specialrule{0.15pt}{0pt}{0pt}\n"

    end
  )


  return
    before ..
    "\n" ..
    body ..
    after
end


-- ---------------------------------------------------------
-- Apply common styling
-- ---------------------------------------------------------

local function apply_table_style(tex, style)

  tex = fix_outer_table_padding(tex)


  -- Top rule + header background

  tex = replace_once(
    tex,
    "\\toprule\\noalign{}",
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\toprule\\noalign{}\n" ..
    "\\rowcolor{" ..
    style.head ..
    "}"
  )


  -- Slightly stronger rule below header

  tex = tex:gsub(
    "\\midrule\\noalign{}",
    "\\arrayrulecolor{tableheadrule}\n" ..
    "\\specialrule{0.35pt}{0pt}{0pt}"
  )


  -- Subtle bottom rule

  tex = tex:gsub(
    "\\bottomrule\\noalign{}",
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\specialrule{0.30pt}{0pt}{0pt}"
  )


  -- Alternating body rows + subtle separators

  tex = color_body_rows(
    tex,
    style.light,
    style.dark
  )


  -- -------------------------------------------------------
  -- Table typography and spacing
  -- -------------------------------------------------------
  --
  -- footnotesize:
  --   smaller than normal body text
  --
  -- baselinestretch:
  --   increases spacing between wrapped text lines
  --
  -- extrarowheight:
  --   adds vertical padding to every table row
  --
  -- arraystretch:
  --   slightly increases the normal table row strut
  --

  tex =
    "\\begingroup\n" ..
    "\\footnotesize\n" ..
    "\\renewcommand{\\baselinestretch}{1.12}\\selectfont\n" ..
    "\\setlength{\\tabcolsep}{5pt}\n" ..
    "\\setlength{\\extrarowheight}{2.5pt}\n" ..
    "\\renewcommand{\\arraystretch}{1.15}\n" ..
    tex ..
    "\n\\endgroup"


  return tex
end


-- =========================================================
-- Unnumbered tables inside ::: {.zebra}
-- =========================================================

function Div(div)

  if FORMAT ~= "latex" then
    return div
  end


  local style = get_style(div)

  if style == nil then
    return div
  end


  local tex = pandoc.write(
    pandoc.Pandoc(div.content),
    "latex"
  )


  tex = apply_table_style(
    tex,
    style
  )


  return pandoc.RawBlock(
    "latex",
    tex
  )

end


-- =========================================================
-- Numbered / cross-referenced tables
-- =========================================================

local function predicate(float)

  return
    FORMAT == "latex"
    and float.type == "Table"
    and get_style(float) ~= nil

end


local function renderer(float)

  local style = get_style(float)


  local tex = pandoc.write(
    pandoc.Pandoc(float.content),
    "latex"
  )


  -- Remove Pandoc's unnumbered longtable marker

  tex = replace_once(
    tex,
    "\\def\\LTcaptype{none} % do not increment counter\n",
    ""
  )


  -- Restore caption + label

  local caption =
    pandoc.utils.stringify(
      float.caption_long
    )


  local caption_latex =
    "\\caption{" ..
    caption ..
    "}\\label{" ..
    float.identifier ..
    "}\\tabularnewline\n"


  tex = fix_outer_table_padding(tex)


  tex = replace_once(
    tex,
    "\\toprule\\noalign{}",
    caption_latex ..
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\toprule\\noalign{}\n" ..
    "\\rowcolor{" ..
    style.head ..
    "}"
  )


  -- Slightly stronger header separator

  tex = tex:gsub(
    "\\midrule\\noalign{}",
    "\\arrayrulecolor{tableheadrule}\n" ..
    "\\specialrule{0.35pt}{0pt}{0pt}"
  )


  -- Bottom rule

  tex = tex:gsub(
    "\\bottomrule\\noalign{}",
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\specialrule{0.30pt}{0pt}{0pt}"
  )


  -- Body rows

  tex = color_body_rows(
    tex,
    style.light,
    style.dark
  )


  -- -------------------------------------------------------
  -- Table typography and spacing
  -- -------------------------------------------------------

  tex =
    "\\begingroup\n" ..
    "\\footnotesize\n" ..
    "\\renewcommand{\\baselinestretch}{1.12}\\selectfont\n" ..
    "\\setlength{\\tabcolsep}{5pt}\n" ..
    "\\setlength{\\extrarowheight}{2.5pt}\n" ..
    "\\renewcommand{\\arraystretch}{1.15}\n" ..
    tex ..
    "\n\\endgroup"


  return pandoc.RawBlock(
    "latex",
    tex
  )

end


quarto._quarto.ast.add_renderer(
  "FloatRefTarget",
  predicate,
  renderer
)
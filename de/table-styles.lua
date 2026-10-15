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
      head = "zebrahead",
      light = "zebralight",
      dark = "zebradark",
      unbreakable = false
    }
  end

  if has_class(el, "zebra_blue") then
    return {
      head = "zebrabluehead",
      light = "zebrabluelight",
      dark = "zebrabluedark",
      unbreakable = true
    }
  end

  return nil
end


-- ---------------------------------------------------------
-- Remove Pandoc's outer @{} from longtable
-- ---------------------------------------------------------

local function fix_outer_table_padding(tex)

  -- Beginning:
  --
  -- \begin{longtable}[]{@{}...
  --
  -- becomes
  --
  -- \begin{longtable}[]{...

  tex = tex:gsub(
    "\\begin{longtable}%[%]%{@%{%}",
    "\\begin{longtable}[]{",
    1
  )


  -- End of column definition:
  --
  -- ...@{}}
  --
  -- becomes
  --
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
-- Color body rows of Pandoc longtable
-- ---------------------------------------------------------

local function color_body_rows(
  tex,
  lightcolor,
  darkcolor
)

  local marker =
    "\\endlastfoot"


  local _, marker_end =
    tex:find(
      marker,
      1,
      true
    )


  if marker_end == nil then
    return tex
  end


  local table_end =
    tex:find(
      "\\end{longtable}",
      marker_end + 1,
      true
    )


  if table_end == nil then
    return tex
  end


  local before =
    tex:sub(
      1,
      marker_end
    )


  local body =
    tex:sub(
      marker_end + 1,
      table_end - 1
    )


  local after =
    tex:sub(
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
-- Apply colors/rules to Pandoc longtable
-- ---------------------------------------------------------

local function style_longtable(
  tex,
  style,
  caption_latex
)

  tex =
    fix_outer_table_padding(
      tex
    )


  -- -------------------------------------------------------
  -- Top rule + optional caption + header background
  -- -------------------------------------------------------

  local top_content = ""


  if caption_latex ~= nil then
    top_content =
      caption_latex
  end


  top_content =
    top_content ..
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\toprule\\noalign{}\n" ..
    "\\rowcolor{" ..
    style.head ..
    "}"


  tex = replace_once(
    tex,
    "\\toprule\\noalign{}",
    top_content
  )


  -- -------------------------------------------------------
  -- Header separator
  -- -------------------------------------------------------

  tex = tex:gsub(
    "\\midrule\\noalign{}",
    "\\arrayrulecolor{tableheadrule}\n" ..
    "\\specialrule{0.35pt}{0pt}{0pt}"
  )


  -- -------------------------------------------------------
  -- Bottom rule
  -- -------------------------------------------------------

  tex = tex:gsub(
    "\\bottomrule\\noalign{}",
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\specialrule{0.30pt}{0pt}{0pt}"
  )


  -- -------------------------------------------------------
  -- Body rows
  -- -------------------------------------------------------

  tex =
    color_body_rows(
      tex,
      style.light,
      style.dark
    )


  return tex
end


-- ---------------------------------------------------------
-- Convert a Pandoc longtable into an ordinary tabular
--
-- Important:
--
-- Pandoc generates special material for longtable:
--
--   \endfirsthead
--   \endhead
--   \endfoot
--   \endlastfoot
--
-- That material exists only to support page breaking and
-- repeated table headers.
--
-- For zebra_blue we remove it and retain:
--
--   first header
--   body
--
-- The resulting tabular is one indivisible TeX object.
-- ---------------------------------------------------------

local function longtable_to_tabular(tex)

  -- -------------------------------------------------------
  -- Determine where Pandoc's longtable header/footer
  -- material begins.
  -- -------------------------------------------------------

  local remove_start = nil


  local firsthead_start =
    tex:find(
      "\\endfirsthead",
      1,
      true
    )


  local head_start =
    tex:find(
      "\\endhead",
      1,
      true
    )


  if firsthead_start ~= nil then

    -- Pandoc supplied a special first header.
    -- Keep the first header and discard everything beginning
    -- with \endfirsthead through \endlastfoot.

    remove_start =
      firsthead_start

  elseif head_start ~= nil then

    -- Normal Pandoc table.
    -- Keep everything before \endhead.

    remove_start =
      head_start

  end


  local _, lastfoot_end =
    tex:find(
      "\\endlastfoot",
      1,
      true
    )


  if remove_start ~= nil
      and lastfoot_end ~= nil then

    tex =
      tex:sub(
        1,
        remove_start - 1
      ) ..
      "\n" ..
      tex:sub(
        lastfoot_end + 1
      )

  end


  -- -------------------------------------------------------
  -- Convert environment
  -- -------------------------------------------------------

  tex = replace_once(
    tex,
    "\\begin{longtable}[]{",
    "\\begin{tabular}{"
  )


  -- Fallback in case Pandoc did not emit [].

  tex = replace_once(
    tex,
    "\\begin{longtable}{",
    "\\begin{tabular}{"
  )


  -- -------------------------------------------------------
  -- longtable's bottom rule was part of its footer and was
  -- removed above. Add our normal bottom rule explicitly.
  -- -------------------------------------------------------

  tex = replace_once(
    tex,
    "\\end{longtable}",
    "\\arrayrulecolor{tableouterrule}\n" ..
    "\\specialrule{0.30pt}{0pt}{0pt}\n" ..
    "\\end{tabular}"
  )


  -- -------------------------------------------------------
  -- Defensive cleanup
  -- -------------------------------------------------------

  tex = tex:gsub(
    "\\endfirsthead%s*",
    ""
  )

  tex = tex:gsub(
    "\\endhead%s*",
    ""
  )

  tex = tex:gsub(
    "\\endfoot%s*",
    ""
  )

  tex = tex:gsub(
    "\\endlastfoot%s*",
    ""
  )


  return tex
end


-- ---------------------------------------------------------
-- Common typography / spacing wrapper
-- ---------------------------------------------------------

local function wrap_table_typography(tex)

  return
    "\\begingroup\n" ..
    "\\footnotesize\n" ..
    "\\renewcommand{\\baselinestretch}{1.12}\\selectfont\n" ..
    "\\setlength{\\tabcolsep}{5pt}\n" ..
    "\\setlength{\\extrarowheight}{2.5pt}\n" ..
    "\\renewcommand{\\arraystretch}{1.15}\n" ..
    tex ..
    "\n\\endgroup"

end


-- =========================================================
-- Unnumbered tables inside:
--
-- ::: {.zebra}
--
-- or
--
-- ::: {.zebra_blue}
-- =========================================================

function Div(div)

  if FORMAT ~= "latex" then
    return div
  end


  local style =
    get_style(
      div
    )


  if style == nil then
    return div
  end


  local tex =
    pandoc.write(
      pandoc.Pandoc(
        div.content
      ),
      "latex"
    )


  -- Remove Pandoc's unnumbered longtable marker if present.

  tex = replace_once(
    tex,
    "\\def\\LTcaptype{none} % do not increment counter\n",
    ""
  )


  -- -------------------------------------------------------
  -- Apply existing table styling
  -- -------------------------------------------------------

  tex =
    style_longtable(
      tex,
      style,
      nil
    )


  -- -------------------------------------------------------
  -- zebra_blue:
  --
  -- Make table unbreakable.
  -- -------------------------------------------------------

  if style.unbreakable then

    tex =
      longtable_to_tabular(
        tex
      )

  end


  tex =
    wrap_table_typography(
      tex
    )


  return
    pandoc.RawBlock(
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

  local style =
    get_style(
      float
    )


  local tex =
    pandoc.write(
      pandoc.Pandoc(
        float.content
      ),
      "latex"
    )


  -- -------------------------------------------------------
  -- Remove Pandoc's unnumbered longtable marker
  -- -------------------------------------------------------

  tex = replace_once(
    tex,
    "\\def\\LTcaptype{none} % do not increment counter\n",
    ""
  )


  -- -------------------------------------------------------
  -- Caption
  -- -------------------------------------------------------

  local caption =
    pandoc.utils.stringify(
      float.caption_long
    )


  -- =======================================================
  -- zebra_blue
  --
  -- Unbreakable table.
  --
  -- Caption belongs to the outer table float.
  -- The actual table is converted to ordinary tabular.
  -- =======================================================

  if style.unbreakable then

    tex =
      style_longtable(
        tex,
        style,
        nil
      )


    tex =
      longtable_to_tabular(
        tex
      )


    tex =
      wrap_table_typography(
        tex
      )


    tex =
      "\\begin{table}[!htbp]\n" ..
      "\\centering\n" ..
      "\\caption{" ..
      caption ..
      "}\\label{" ..
      float.identifier ..
      "}\n" ..
      tex ..
      "\n\\end{table}"


    return
      pandoc.RawBlock(
        "latex",
        tex
      )

  end


  -- =======================================================
  -- zebra
  --
  -- Existing breakable longtable behaviour.
  -- =======================================================


  local caption_latex =
    "\\caption{" ..
    caption ..
    "}\\label{" ..
    float.identifier ..
    "}\\tabularnewline\n"


  tex =
    style_longtable(
      tex,
      style,
      caption_latex
    )


  tex =
    wrap_table_typography(
      tex
    )


  return
    pandoc.RawBlock(
      "latex",
      tex
    )

end


quarto._quarto.ast.add_renderer(
  "FloatRefTarget",
  predicate,
  renderer
)
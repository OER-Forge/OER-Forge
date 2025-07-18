accessibility_results    conversion_results       site_info              
content                  files                  
conversion_capabilities  pages_files            

## Table: accessibility_results
Columns: id,content_id,pa11y_json,badge_html,wcag_level,error_count,warning_count,notice_count,checked_at,status,reason,custom_label,forced,created_at

## Table: conversion_results
Columns: id,content_id,source_format,target_format,output_path,conversion_time,status,reason,forced,custom_label,created_at

## Table: site_info
Columns: id,title,author,description,logo,favicon,theme_default,theme_light,theme_dark,language,github_url,footer_text,header

## Table: content
Columns: id,title,source_path,output_path,is_autobuilt,mime_type,parent_output_path,parent_slug,slug,is_section_index,wcag_status_html,can_convert_md,can_convert_tex,can_convert_pdf,can_convert_docx,can_convert_ppt,can_convert_jupyter,can_convert_ipynb,relative_link,menu_context,level,export_types,export_force,export_custom_label,export_output_path
id  title                          source_path                   output_path                                        is_autobuilt  mime_type  parent_output_path                 parent_slug       slug              is_section_index  wcag_status_html  can_convert_md  can_convert_tex  can_convert_pdf  can_convert_docx  can_convert_ppt  can_convert_jupyter  can_convert_ipynb  relative_link                                menu_context  level  export_types                   export_force  export_custom_label  export_output_path
--  -----------------------------  ----------------------------  -------------------------------------------------  ------------  ---------  ---------------------------------  ----------------  ----------------  ----------------  ----------------  --------------  ---------------  ---------------  ----------------  ---------------  -------------------  -----------------  -------------------------------------------  ------------  -----  -----------------------------  ------------  -------------------  ------------------
1   Home                           content/index.md              build/home/index.html                              0             .md                                                             home              0                                   1               1                1                1                 1                1                    0                  home/index.html                              main          0      html,md,docx,pdf,tex,txt,epub  0                                  build/{slug}/files
2   Sample                         content/sample/index.md       build/sample-resources/index.html                  0             .md                                           sample-resources  sample-resources  1                                   1               1                1                1                 1                1                    0                  sample-resources/index.html                  main          0      html,md,docx,pdf,tex,txt,epub  0                                  build/{slug}/files
3   Introduction to Newton's Laws  content/sample/newton.md      build/sample-resources/newton/newton.html          0             .md        build/sample-resources/index.html  sample-resources  newton            0                                   1               1                1                1                 1                1                    0                  sample-resources/newton/newton.html          main          1      html,md,docx,pdf,tex,txt,epub  0                                  build/{slug}/files
4   Sample Activities              content/sample/activities.md  build/sample-resources/activities/activities.html  0             .md        build/sample-resources/index.html  sample-resources  activities        0                                   1               1                1                1                 1                1                    0                  sample-resources/activities/activities.html  main          1      html,md,docx,pdf,tex,txt,epub  0                                  build/{slug}/files
5   About                          content/about.md              build/about/about.html                             0             .md                                                             about             0                                   1               1                1                1                 1                1                    0                  about/about.html                             main          0      html,md,docx,pdf,tex,txt,epub  0                                  build/{slug}/files

## Table: files
Columns: id,filename,extension,mime_type,is_image,is_remote,url,referenced_page,relative_path,absolute_path,cell_type,is_code_generated,is_embedded,has_local_copy
id  filename                                     extension  mime_type      is_image  is_remote  url                                                                       referenced_page   relative_path                                                             absolute_path                                                                         cell_type  is_code_generated  is_embedded  has_local_copy
--  -------------------------------------------  ---------  -------------  --------  ---------  ------------------------------------------------------------------------  ----------------  ------------------------------------------------------------------------  ------------------------------------------------------------------------------------  ---------  -----------------  -----------  --------------
1   index.md                                     .md        text/markdown  0         0                                                                                                      content/index.md                                                          /Users/caballero/repos/oerforge/OER-Forge/content/index.md                                                                       1             
2   index.md                                     .md        text/markdown  0         0                                                                                                      content/sample/index.md                                                   /Users/caballero/repos/oerforge/OER-Forge/content/sample/index.md                                                                1             
3   newton.md                                    .md        text/markdown  0         0                                                                                                      content/sample/newton.md                                                  /Users/caballero/repos/oerforge/OER-Forge/content/sample/newton.md                                                               1             
4   activities.md                                .md        text/markdown  0         0                                                                                                      content/sample/activities.md                                              /Users/caballero/repos/oerforge/OER-Forge/content/sample/activities.md                                                           1             
5   about.md                                     .md        text/markdown  0         0                                                                                                      content/about.md                                                          /Users/caballero/repos/oerforge/OER-Forge/content/about.md                                                                       1             
6   OER-Forge                                               image/png      1         1          https://img.shields.io/github/issues-pr/OER-Forge/OER-Forge               content/index.md  https://img.shields.io/github/last-commit/OER-Forge/OER-Forge             https://img.shields.io/github/last-commit/OER-Forge/OER-Forge                                                                                  
7   license-CC%20BY--NC--SA%204.0-lightgrey.svg  .svg       image/png      1         1          https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg  content/index.md  https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg  https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey.svg                                                                       
8   logo.png                                     .png       image/png      1         0                                                                                    content/index.md  images/logo.png                                                           /Users/caballero/repos/oerforge/OER-Forge/content/images/logo.png                                                                              
9   sample.png                                   .png       image/png      1         0                                                                                    content/about.md  images/sample.png                                                         /Users/caballero/repos/oerforge/OER-Forge/content/images/sample.png                                                                            
10  textbooks-vs-inflation.webp                  .webp      image/png      1         0                                                                                    content/about.md  ./images/textbooks-vs-inflation.webp                                      /Users/caballero/repos/oerforge/OER-Forge/content/images/textbooks-vs-inflation.webp                                                           

## Table: conversion_capabilities
Columns: id,source_format,target_format,is_enabled
id  source_format  target_format  is_enabled
--  -------------  -------------  ----------
1   .md            .txt           1         
2   .md            .md            1         
3   .md            .marp          1         
4   .md            .tex           1         
5   .md            .pdf           1         
6   .md            .docx          1         
7   .md            .ppt           1         
8   .md            .jupyter       1         
9   .md            .epub          1         
10  .marp          .txt           1         
11  .marp          .md            1         
12  .marp          .marp          1         
13  .marp          .pdf           1         
14  .marp          .docx          1         
15  .marp          .ppt           1         
16  .tex           .txt           1         
17  .tex           .md            1         
18  .tex           .tex           1         
19  .tex           .pdf           1         
20  .tex           .docx          1         
21  .ipynb         .txt           1         
22  .ipynb         .md            1         
23  .ipynb         .tex           1         
24  .ipynb         .pdf           1         
25  .ipynb         .docx          1         
26  .ipynb         .jupyter       1         
27  .ipynb         .ipynb         1         
28  .jupyter       .md            1         
29  .jupyter       .tex           1         
30  .jupyter       .pdf           1         
31  .jupyter       .docx          1         
32  .jupyter       .jupyter       1         
33  .jupyter       .ipynb         1         
34  .docx          .txt           1         
35  .docx          .md            1         
36  .docx          .tex           1         
37  .docx          .pdf           1         
38  .docx          .docx          1         
39  .ppt           .txt           1         
40  .ppt           .ppt           1         
41  .txt           .txt           1         
42  .txt           .md            1         
43  .txt           .tex           1         
44  .txt           .docx          1         
45  .txt           .pdf           1         

## Table: pages_files
Columns: id,file_id,page_path

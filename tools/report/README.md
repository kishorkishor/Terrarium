# Report builder

Generates `TERRARIUM-Report.docx` (department cover + rubric pages, then the paper in
IEEE conference A4 two-column format) from the figures in `assets/`.

```
cd tools/report
npm install docx@9
node build_report.js          # writes ../../TERRARIUM-Report.docx
```

PDF export: open the .docx in Word and Save As PDF (or the Word COM one-liner in the
project notes). Figures were exported from the presentation deck; `hysteresis.png`
is generated with the firmware defaults (mist on < 75 % RH, off > 90 % RH).

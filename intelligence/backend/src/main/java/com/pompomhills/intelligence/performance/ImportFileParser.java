package com.pompomhills.intelligence.performance;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.poi.ss.usermodel.DataFormatter;
import org.apache.poi.ss.usermodel.WorkbookFactory;
import org.springframework.stereotype.Component;

@Component
class ImportFileParser {
  ParsedFile parse(String filename, InputStream input) throws IOException {
    return switch (extension(filename)) {
      case "csv" -> parseDelimited(input, ',');
      case "tsv" -> parseDelimited(input, '\t');
      case "xlsx" -> parseWorkbook(input);
      default ->
          throw new IllegalArgumentException("Only CSV, TSV, and XLSX imports are supported");
    };
  }

  private ParsedFile parseDelimited(InputStream input, char delimiter) throws IOException {
    var format =
        CSVFormat.DEFAULT
            .builder()
            .setDelimiter(delimiter)
            .setHeader()
            .setSkipHeaderRecord(true)
            .setIgnoreEmptyLines(true)
            .setTrim(true)
            .get();
    try (var parser = CSVParser.parse(input, StandardCharsets.UTF_8, format)) {
      var rows = new ArrayList<ParsedRow>();
      for (var record : parser) {
        rows.add(
            new ParsedRow("data", Math.toIntExact(record.getRecordNumber() + 1), record.toMap()));
      }
      return new ParsedFile(List.copyOf(parser.getHeaderNames()), rows);
    }
  }

  private ParsedFile parseWorkbook(InputStream input) throws IOException {
    try (var workbook = WorkbookFactory.create(input)) {
      var allHeaders = new ArrayList<String>();
      var rows = new ArrayList<ParsedRow>();
      var formatter = new DataFormatter(Locale.ROOT);
      for (var sheet : workbook) {
        if (sheet.getPhysicalNumberOfRows() == 0) continue;
        var headerRow = sheet.getRow(sheet.getFirstRowNum());
        if (headerRow == null) continue;
        var headers = new ArrayList<String>();
        for (int column = 0; column < headerRow.getLastCellNum(); column++) {
          String value = formatter.formatCellValue(headerRow.getCell(column)).trim();
          headers.add(value.isBlank() ? "column_" + (column + 1) : value);
        }
        headers.forEach(
            header -> {
              if (!allHeaders.contains(header)) allHeaders.add(header);
            });
        for (int index = headerRow.getRowNum() + 1; index <= sheet.getLastRowNum(); index++) {
          var row = sheet.getRow(index);
          if (row == null) continue;
          var values = new LinkedHashMap<String, String>();
          boolean hasValue = false;
          for (int column = 0; column < headers.size(); column++) {
            String value = formatter.formatCellValue(row.getCell(column)).trim();
            values.put(headers.get(column), value);
            hasValue |= !value.isBlank();
          }
          if (hasValue) rows.add(new ParsedRow(sheet.getSheetName(), index + 1, values));
        }
      }
      return new ParsedFile(allHeaders, rows);
    }
  }

  private String extension(String filename) {
    int dot = filename.lastIndexOf('.');
    return dot < 0 ? "" : filename.substring(dot + 1).toLowerCase(Locale.ROOT);
  }

  record ParsedFile(List<String> columns, List<ParsedRow> rows) {}

  record ParsedRow(String sheet, int rowNumber, Map<String, String> values) {}
}

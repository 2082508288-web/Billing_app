"""Consistent UTF-8 CSV exports of the currently displayed report."""
import csv
from PySide6.QtWidgets import QFileDialog, QMessageBox


def export_csv(parent, title, filename, headers, rows):
    path, _ = QFileDialog.getSaveFileName(parent, title, filename, 'CSV Files (*.csv)')
    if not path:
        return
    try:
        with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.writer(stream)
            writer.writerow(headers)
            for row in rows:
                # User-entered names/notes are text, never spreadsheet formulas.
                writer.writerow(["'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in row])
    except OSError as exc:
        QMessageBox.warning(parent, 'Export failed', str(exc))
        return
    QMessageBox.information(parent, 'Exported', f'Saved to:\n{path}')

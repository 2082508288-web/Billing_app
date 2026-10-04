"""Local database information, backup, and export."""
import os
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTextEdit, QFileDialog, QMessageBox)
from widgets import make_heading


class StatusTab(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.addWidget(make_heading("Data & Backups", "Your shop data is stored on this computer"))
        location = QLabel(f"Database location:\n{db.path}")
        location.setWordWrap(True)
        layout.addWidget(location)
        help_text = QLabel("Create a database backup for safekeeping, or export your records as CSV files.")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        buttons = QHBoxLayout()
        backup = QPushButton("Back Up Database")
        backup.clicked.connect(self.backup_database_now)
        buttons.addWidget(backup)
        export = QPushButton("Export All Records (CSV)")
        export.setProperty("role", "secondary")
        export.clicked.connect(self.export_database_csv)
        buttons.addWidget(export)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Backup and export results appear here.")
        layout.addWidget(self.output)

    def append_output(self, text):
        self.output.append(text)

    def backup_database_now(self):
        if self.db is None:
            QMessageBox.warning(self, "No database", "No database is connected.")
            return
        try:
            path = self.db.backup_database()
        except Exception as exc:
            QMessageBox.warning(self, "Backup failed", str(exc))
            self.append_output(f"Backup failed: {exc}")
            return
        self.append_output(f"Backup saved: {path}")
        QMessageBox.information(
            self,
            "Backup complete",
            f"A copy of the database was saved to:\n\n{path}",
        )

    def export_database_csv(self):
        if self.db is None:
            QMessageBox.warning(self, "No database", "No database is connected.")
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Choose a folder to export CSV files into"
        )
        if not folder:
            return
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        export_dir = os.path.join(folder, f"cloth_shop_csv_export_{stamp}")
        try:
            files = self.db.export_all_tables_csv(export_dir)
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
            self.append_output(f"CSV export failed: {exc}")
            return
        self.append_output(f"Exported {len(files)} CSV file(s) to: {export_dir}")
        QMessageBox.information(
            self,
            "Export complete",
            f"Exported {len(files)} table(s) as CSV to:\n\n{export_dir}",
        )

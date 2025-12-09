import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QFileDialog, 
                             QLabel, QProgressBar, QMessageBox, QFrame, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent, QPixmap

from converter import Md2PdfConverter
from editor import EditorWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Md2PDF")
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
        
        # Load Stylesheet
        self.load_stylesheet()
        
        # Main Layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)


        # Logo
        logo_label = QLabel()
        project_root = os.path.dirname(os.path.dirname(__file__))
        logo_path = os.path.join(project_root, "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaledToHeight(60, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            logo_label.setStyleSheet("padding-left: 5px;")
            layout.addWidget(logo_label)

        # Header
        header = QLabel("MD Dosyalarınızı Dönüştürün")
        header.setObjectName("headerLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Instructions
        instr = QLabel("Dosyaları buraya sürükleyip bırakın veya 'Dosya Ekle' butonunu kullanın.")
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr.setStyleSheet("color: #a6adc8; font-style: italic;")
        layout.addWidget(instr)

        # File List
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.itemDoubleClicked.connect(self.edit_file)
        layout.addWidget(self.file_list)

        # Buttons Layout
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Dosya Ekle")
        self.btn_add.clicked.connect(self.add_files)
        
        self.btn_remove = QPushButton("Seçiliyi Sil")
        self.btn_remove.setObjectName("deleteButton")
        self.btn_remove.clicked.connect(self.remove_files)
        
        self.btn_clear = QPushButton("Listeyi Temizle")
        self.btn_clear.clicked.connect(self.file_list.clear)

        btn_layout.addWidget(self.btn_add)
        
        self.btn_new = QPushButton("Yeni Dosya")
        self.btn_new.clicked.connect(self.new_file)
        btn_layout.addWidget(self.btn_new)
        
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # Output Directory Selection
        dir_layout = QHBoxLayout()
        self.lbl_output = QLabel("Çıktı Klasörü: Kaynak ile aynı")
        self.lbl_output.setStyleSheet("font-size: 12px; color: #bac2de;")
        
        self.btn_select_output = QPushButton("Çıktı Klasörü Seç")
        self.btn_select_output.clicked.connect(self.select_output_dir)
        
        dir_layout.addStretch()
        dir_layout.addWidget(self.btn_select_output)
        layout.addLayout(dir_layout)

        # Checkbox for Word Conversion
        self.chk_docx = QCheckBox("Word (.docx) formatına da dönüştür")
        self.chk_docx.setStyleSheet("color: #bac2de; font-size: 13px;")
        layout.addWidget(self.chk_docx)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #313244;")
        layout.addWidget(line)

        # Convert Button
        self.btn_convert = QPushButton("PDF'e Dönüştür")
        self.btn_convert.setObjectName("convertButton")
        self.btn_convert.clicked.connect(self.start_conversion)
        layout.addWidget(self.btn_convert)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status Label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # State
        self.output_dir = None
        self.converter = Md2PdfConverter()

    def load_stylesheet(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), "styles.qss"), "r") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Stil dosyası yüklenemedi: {e}")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_file_paths(files)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "MD Dosyaları Seç", "", "Markdown Files (*.md);;All Files (*)")
        if files:
            self.add_file_paths(files)

    def add_file_paths(self, paths):
        for path in paths:
            if path.lower().endswith('.md'):
                # Avoid duplicates
                items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
                if path not in items:
                    self.file_list.addItem(path)

    def remove_files(self):
        for item in self.file_list.selectedItems():
            self.file_list.takeItem(self.file_list.row(item))

    def select_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Çıktı Klasörü Seç")
        if directory:
            self.output_dir = directory
            self.lbl_output.setText(f"Çıktı: {directory}")

    def edit_file(self, item):
        file_path = item.text()
        self.editor_window = EditorWindow(file_path, self)
        self.editor_window.show()

    def new_file(self):
        self.editor_window = EditorWindow(None, self)
        self.editor_window.show()

    def start_conversion(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen dönüştürülecek dosya ekleyin.")
            return

        self.btn_convert.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Hazırlanıyor...")

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        total = len(files)
        
        # Process in main thread to avoid QPainter/Font issues on Windows
        for i, file_path in enumerate(files):
            filename = os.path.basename(file_path)
            self.status_label.setText(f"Dönüştürülüyor: {filename}...")
            QApplication.processEvents() # Keep UI responsive
            
            # Determine Output Path
            if self.output_dir:
                pdf_dir = self.output_dir
            else:
                pdf_dir = os.path.dirname(file_path)
                
            base_name = os.path.splitext(filename)[0] + ".pdf"
            output_path = os.path.join(pdf_dir, base_name)
            
            success = self.converter.convert(file_path, output_path)
            
            if success:
                if self.chk_docx.isChecked():
                    self.status_label.setText(f"Word'e çevriliyor: {filename}...")
                    QApplication.processEvents()
                    try:
                        self.converter.convert_to_docx(output_path)
                    except Exception as e:
                        print(f"DOCX Hata: {e}")
            else:
               print(f"Hata: {filename}")
            
            self.progress_bar.setValue(int(((i + 1) / total) * 100))

        self.status_label.setText("İşlem Tamamlandı!")
        self.btn_convert.setEnabled(True)
        QMessageBox.information(self, "Başarılı", "Tüm dosyalar dönüştürüldü!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

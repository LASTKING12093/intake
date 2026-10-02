"""Compose a repository sharing card from the actual application screenshot."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QApplication
from app.ui.assets import font_family
app = QApplication([])
canvas = QImage(1280, 640, QImage.Format.Format_RGB32)
canvas.fill(QColor('#030303'))
p = QPainter(canvas)
p.setRenderHint(QPainter.RenderHint.Antialiasing)
p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
family = font_family()
font = QFont(family); font.setPixelSize(54); font.setWeight(QFont.Weight.Medium)
p.setFont(font); p.setPen(QColor('#ffffff')); p.drawText(52, 264, 'INTAKE')
font.setPixelSize(19); font.setWeight(QFont.Weight.Normal); p.setFont(font)
p.setPen(QColor('#c4c4c4')); p.drawText(54, 310, 'Universal Media Downloader')
p.setPen(QColor('#ffffff')); p.drawText(54, 362, 'Take it in. Keep it yours.')
font.setPixelSize(14); p.setFont(font); p.setPen(QColor('#929292'))
p.drawText(54, 550, 'OPEN SOURCE  /  WINDOWS')
rect = QRectF(424, 72, 820, 512.5)
p.setBrush(QColor('#111111')); p.setPen(QColor('#353535')); p.drawRoundedRect(rect.adjusted(-1,-1,1,1), 18, 18)
clip = QPainterPath(); clip.addRoundedRect(rect, 18, 18)
p.setClipPath(clip)
p.drawImage(rect, QImage(str(ROOT / 'docs/assets/detected-media.png')))
p.end()
assert canvas.save(str(ROOT / 'docs/assets/social-preview.png'))

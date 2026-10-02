from pathlib import Path
import sys,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt,QRectF,QBuffer,QIODevice
from PySide6.QtGui import QImage,QPainter,QColor,QLinearGradient,QPen
from PySide6.QtWidgets import QApplication
from app.widgets.surfaces import draw_mark
app=QApplication.instance() or QApplication([])
folder=Path(__file__).resolve().parents[1]/'app'/'resources'; folder.mkdir(parents=True,exist_ok=True)
images=[]
for size in (16,24,32,48,64,128,256):
 image=QImage(size,size,QImage.Format.Format_ARGB32); image.fill(Qt.GlobalColor.transparent)
 p=QPainter(image); p.setRenderHint(QPainter.RenderHint.Antialiasing)
 g=QLinearGradient(0,0,size,size); g.setColorAt(0,QColor('#202020')); g.setColorAt(.45,QColor('#080808')); g.setColorAt(1,QColor('#000000'))
 p.setBrush(g); p.setPen(QPen(QColor('#444444'),max(.6,size/256))); p.drawRoundedRect(QRectF(.5,.5,size-1,size-1),size*.23,size*.23)
 draw_mark(p,QRectF(size*.19,size*.19,size*.62,size*.62)); p.end()
 buffer=QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly); image.save(buffer,'PNG'); images.append((size,bytes(buffer.data())))
 if size in (16,256): image.save(str(folder/('icon.png' if size==256 else 'icon-16.png')))
offset=6+16*len(images); directory=bytearray(struct.pack('<HHH',0,1,len(images))); payload=bytearray()
for size,data in images:
 directory.extend(struct.pack('<BBBBHHII',size%256,size%256,0,0,1,32,len(data),offset)); payload.extend(data); offset+=len(data)
(folder/'icon.ico').write_bytes(directory+payload)
(folder/'mark.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><defs><path id="fold" d="M16 2C23.7 2 30 8.3 30 16C26 11.8 21.5 11.6 18.7 15.2C17.1 17.2 14.6 17.1 13.7 15.1C12.5 12.3 16 9.9 16 6.3Z"/></defs><g fill="#fff"><use href="#fold"/><use href="#fold" transform="rotate(120 16 16)"/><use href="#fold" transform="rotate(240 16 16)"/></g></svg>')

"""Licensed SVG assets; preserve platform colors and tint only utility icons."""
from functools import lru_cache
from pathlib import Path
import sys
from PySide6.QtCore import Qt,QRectF,QByteArray
from PySide6.QtGui import QIcon,QPixmap,QPainter,QFontDatabase
from PySide6.QtSvg import QSvgRenderer
from app.utils.paths import root_dir


def resources(): return Path(getattr(sys,'_MEIPASS',root_dir()))/'app'/'resources'

@lru_cache(maxsize=128)
def icon(name,color='#cccccc',size=24):
    text=(resources()/'icons'/(name+'.svg')).read_text('utf-8')
    if name in {'youtube','tiktok','spotify','applemusic'}: pass
    elif 'currentColor' in text: text=text.replace('currentColor',color).replace('stroke-width="2"','stroke-width="1.6"')
    else: text=text.replace('<svg ',f'<svg fill="{color}" ')
    renderer=QSvgRenderer(QByteArray(text.encode())); pixmap=QPixmap(size*2,size*2); pixmap.fill(Qt.GlobalColor.transparent)
    bounds=renderer.viewBoxF(); factor=min(size*2/bounds.width(),size*2/bounds.height())
    width,height=bounds.width()*factor,bounds.height()*factor
    painter=QPainter(pixmap); renderer.render(painter,QRectF((size*2-width)/2,(size*2-height)/2,width,height)); painter.end(); pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)

_loaded=False

def font_family():
    global _loaded
    if not _loaded:
        for file in (resources()/'fonts').glob('*.ttf'): QFontDatabase.addApplicationFont(str(file))
        _loaded=True
    families=QFontDatabase.families()
    return next((name for name in ('SF Pro Text','SF Pro','Inter','Segoe UI') if name in families),'Segoe UI')

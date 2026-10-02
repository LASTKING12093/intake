"""Native reusable surfaces, navigation, composer and progress feedback."""
import math
from PySide6.QtCore import Qt, QRectF, QPointF, Property, Signal, QTimer, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QLinearGradient, QRadialGradient, QPainterPath, QIcon, QPixmap
from PySide6.QtWidgets import QWidget, QFrame, QPushButton, QPlainTextEdit, QHBoxLayout, QVBoxLayout, QMenu, QProgressBar, QLabel
from app.ui.tokens import COLORS, RADIUS
from app.ui.motion import Motion
from app.widgets.common import label
from app.utils.urls import source_name, parse_urls
from app.ui.assets import icon

class AmbientPage(QWidget):
    def paintEvent(self,event):
        p=QPainter(self); p.save(); p.fillRect(self.rect(),QColor('#000000'))
        light=QRadialGradient(QPointF(self.width()*.52,self.height()*.52),self.width()*.65)
        light.setColorAt(0,QColor(255,255,255,3)); light.setColorAt(.6,QColor(255,255,255,0)); light.setColorAt(1,QColor(0,0,0,0))
        p.fillRect(self.rect(),light); p.restore(); p.end()


def draw_mark(p, rect, color='#ffffff'):
    # Three receiving folds converge around a small negative-space opening.
    p.save(); p.translate(rect.x(),rect.y()); p.scale(rect.width()/32,rect.height()/32)
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(color))
    fold=QPainterPath(); fold.moveTo(16,2)
    fold.cubicTo(23.7,2,30,8.3,30,16)
    fold.cubicTo(26,11.8,21.5,11.6,18.7,15.2)
    fold.cubicTo(17.1,17.2,14.6,17.1,13.7,15.1)
    fold.cubicTo(12.5,12.3,16,9.9,16,6.3); fold.closeSubpath()
    for angle in (0,120,240):
        p.save(); p.translate(16,16); p.rotate(angle); p.translate(-16,-16); p.drawPath(fold); p.restore()
    p.restore()

class BrandMark(QWidget):
    def __init__(self, size=32, parent=None):
        super().__init__(parent); self.setFixedSize(size, size); self.setAccessibleName('INTAKE')
    def paintEvent(self, event):
        p=QPainter(self); p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing); draw_mark(p,QRectF(self.rect()).adjusted(2,2,-2,-2)); p.restore(); p.end()

class Artwork(QLabel):
    """Rounded native image well; thumbnail workers can use QLabel's setPixmap API."""
    def paintEvent(self,event):
        p=QPainter(self); p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path=QPainterPath(); path.addRoundedRect(QRectF(self.rect()),12,12); p.setClipPath(path); p.fillPath(path,QColor('#111111'))
        pixmap=self.pixmap()
        if pixmap and not pixmap.isNull():
            w=pixmap.width()/pixmap.devicePixelRatio(); h=pixmap.height()/pixmap.devicePixelRatio()
            p.drawPixmap(QPointF((self.width()-w)/2,(self.height()-h)/2),pixmap)
        p.restore(); p.end()

class GlassSurface(QFrame):
    def __init__(self, parent=None, radius=None):
        super().__init__(parent)
        self.radius = radius or RADIUS['surface']; self._light=0.0
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
    def get_light(self): return self._light
    def set_light(self, value): self._light=value; self.update()
    light = Property(float, get_light, set_light)
    def enterEvent(self,event):
        Motion.animate(self,b'light',1.0,'quick'); super().enterEvent(event)
    def leaveEvent(self,event):
        Motion.animate(self,b'light',0.0,'soft'); super().leaveEvent(event)
    def paintEvent(self,event):
        p=QPainter(self); p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=QRectF(self.rect()).adjusted(2,2,-2,-3)
        path=QPainterPath(); path.addRoundedRect(rect,self.radius,self.radius)
        # A transparent pane with a narrow optical rim. The center remains dark.
        p.setClipPath(path)
        p.fillPath(path,QColor(16,16,16,155))
        volume=QLinearGradient(0,0,0,self.height())
        volume.setColorAt(0,QColor(255,255,255,10)); volume.setColorAt(.15,QColor(255,255,255,2)); volume.setColorAt(.7,QColor(255,255,255,0)); volume.setColorAt(1,QColor(255,255,255,9))
        p.fillPath(path,volume)
        reflection=QRadialGradient(QPointF(self.width()*.1,-self.height()*.2),self.width()*.45)
        reflection.setColorAt(0,QColor(255,255,255,12+int(9*self._light))); reflection.setColorAt(1,QColor(255,255,255,0)); p.fillPath(path,reflection)
        # Reflected caustic follows the curved lip rather than filling the panel gray.
        rim=QLinearGradient(0,0,self.width(),self.height())
        rim.setColorAt(0,QColor(255,255,255,160)); rim.setColorAt(.18,QColor(255,255,255,45)); rim.setColorAt(.5,QColor(255,255,255,10)); rim.setColorAt(.8,QColor(255,255,255,30)); rim.setColorAt(1,QColor(255,255,255,110))
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(rim,1.2)); p.drawPath(path)
        lens=QLinearGradient(0,0,0,self.height()); lens.setColorAt(0,QColor(255,255,255,26)); lens.setColorAt(.3,QColor(255,255,255,3)); lens.setColorAt(.8,QColor(255,255,255,2)); lens.setColorAt(1,QColor(255,255,255,25))
        p.setPen(QPen(lens,2.5)); p.drawRoundedRect(rect.adjusted(2,2,-2,-2),self.radius-2,self.radius-2)
        p.setPen(QPen(QColor(0,0,0,130),1)); p.drawRoundedRect(rect.adjusted(4,4,-4,-4),self.radius-4,self.radius-4)
        p.setPen(QColor(255,255,255,3))
        for y in range(6,self.height(),11):
            for x in range((y*7)%17,self.width(),17): p.drawPoint(x,y)
        p.restore(); p.end()

class NavigationDot(QWidget):
    def paintEvent(self,event):
        p=QPainter(self); p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor('#ffffff'))
        p.drawEllipse(QRectF(self.rect())); p.restore(); p.end()

class NavigationButton(QPushButton):
    def __init__(self,text,parent=None):
        super().__init__(text,parent); self._scale=1.0
    def get_scale(self): return self._scale
    def set_scale(self,value): self._scale=value; self.update()
    scale=Property(float,get_scale,set_scale)
    def enterEvent(self,event):
        Motion.animate(self,b'scale',1.05,'quick'); super().enterEvent(event)
    def leaveEvent(self,event):
        Motion.animate(self,b'scale',1.0,'spring'); super().leaveEvent(event)
    def mousePressEvent(self,event):
        Motion.animate(self,b'scale',.94,'quick'); super().mousePressEvent(event)
    def mouseReleaseEvent(self,event):
        Motion.animate(self,b'scale',1.05 if self.underMouse() else 1.0,'spring'); super().mouseReleaseEvent(event)
    def paintEvent(self,event):
        from PySide6.QtWidgets import QStylePainter,QStyleOptionButton,QStyle
        p=QStylePainter(self); p.save(); p.translate(self.width()/2,self.height()/2); p.scale(self._scale,self._scale); p.translate(-self.width()/2,-self.height()/2)
        option=QStyleOptionButton(); self.initStyleOption(option); p.drawControl(QStyle.ControlElement.CE_PushButton,option); p.restore(); p.end()

class Popover(QMenu):
    def showEvent(self,event):
        super().showEvent(event)
        Motion.animate(self,b'windowOpacity',1.0,'quick',start=0.0)

ContextMenu=Popover

class DownloadButton(QPushButton):
    def __init__(self,text,callback,parent=None):
        super().__init__(text,parent); self.setObjectName('primary'); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(callback); self.setMinimumWidth(124); self.setFixedHeight(44); self.setAccessibleName(text)
        self._press=1.0
    def get_press(self): return self._press
    def set_press(self,value): self._press=value; self.update()
    pressScale=Property(float,get_press,set_press)
    def mousePressEvent(self,event):
        Motion.animate(self,b'pressScale',.98,'quick'); super().mousePressEvent(event)
    def mouseReleaseEvent(self,event):
        Motion.animate(self,b'pressScale',1.0,'spring'); super().mouseReleaseEvent(event)
    def paintEvent(self,event):
        from PySide6.QtWidgets import QStylePainter,QStyleOptionButton,QStyle
        p=QStylePainter(self); p.save(); p.translate(self.width()/2,self.height()/2); p.scale(self._press,self._press); p.translate(-self.width()/2,-self.height()/2)
        option=QStyleOptionButton(); self.initStyleOption(option); p.drawControl(QStyle.ControlElement.CE_PushButton,option); p.restore(); p.end()

class ProgressIndicator(QProgressBar):
    def __init__(self,parent=None):
        super().__init__(parent); self.setTextVisible(False); self.setRange(0,1000); self.setAccessibleName('Download progress')
    def progress(self,value,busy=False):
        self.setRange(0,0 if busy else 1000)
        if not busy: Motion.animate(self,b'value',int(value*10))

class PasteInput(QPlainTextEdit):
    submitted=Signal()
    pasted=Signal()
    def insertFromMimeData(self,source):
        super().insertFromMimeData(source); self.pasted.emit()
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.submitted.emit(); event.accept()
        else: super().keyPressEvent(event)

class SourceSelector(QPushButton):
    sources=('Auto Detect','YouTube','TikTok','Spotify','Apple Music')
    def __init__(self,parent=None):
        super().__init__('Auto Detect',parent); self.manual='Auto Detect'; self.detected='Auto Detect'
        self.setObjectName('source'); self.setMinimumWidth(170); self.setFixedHeight(44); self.setIcon(icon('sparkles',size=18)); self.setIconSize(QSize(18,18)); self.setAccessibleName('Select source, automatic detection by default')
        self.menu=Popover(self)
        for name in self.sources:
            action=self.menu.addAction(name); action.setIcon(icon({'YouTube':'youtube','TikTok':'tiktok','Spotify':'spotify','Apple Music':'applemusic'}.get(name,'sparkles'),size=18)); action.setCheckable(True); action.setData(name)
        self.menu.triggered.connect(lambda action: self.select(action.data()))
        self.clicked.connect(self.open_menu)
    def open_menu(self):
        for action in self.menu.actions(): action.setChecked(action.data()==self.manual)
        self.menu.popup(self.mapToGlobal(self.rect().bottomLeft()))
    def select(self,name):
        self.manual=name; self.render()
    def detect(self,text):
        urls=parse_urls(text); self.detected=source_name(urls[0]) if urls else 'Auto Detect'; self.render()
    def render(self):
        name=self.detected if self.manual=='Auto Detect' else self.manual
        if name=='Compatible source': name='Auto Detect'
        text=name
        if text!=self.text():
            self.setText(text); self.setIcon(icon({'YouTube':'youtube','TikTok':'tiktok','Spotify':'spotify','Apple Music':'applemusic'}.get(name,'sparkles'),size=18)); Motion.appear(self)
    def paintEvent(self,event):
        super().paintEvent(event); p=QPainter(self); p.save(); icon('chevron-down',size=14).paint(p,self.width()-22,(self.height()-14)//2,14,14); p.restore(); p.end()

def platform_badge(source, size=18):
    badge=QLabel(); badge.setFixedSize(size,size); badge.setAccessibleName(source)
    name={'YouTube':'youtube','TikTok':'tiktok','Spotify':'spotify','Apple Music':'applemusic'}.get(source,'video')
    badge.setPixmap(icon(name,size=size).pixmap(size,size)); badge.setToolTip(source)
    return badge

class Composer(GlassSurface):
    submitted=Signal()
    def __init__(self,parent=None):
        super().__init__(parent)
        outer=QVBoxLayout(self); outer.setContentsMargins(16,16,16,16); outer.setSpacing(0)
        row=QHBoxLayout(); row.setSpacing(12)
        self.source=SourceSelector(); row.addWidget(self.source)
        divider=QFrame(); divider.setFrameShape(QFrame.Shape.VLine); divider.setStyleSheet('color:#4b4d4e'); divider.setFixedHeight(26); row.addWidget(divider)
        self.input=PasteInput(); self.input.setObjectName('url'); self.input.setPlaceholderText('Paste anything…'); self.input.setFixedHeight(48)
        self.input.setTabChangesFocus(True); self.input.setAccessibleName('Media link. Paste one or more URLs; Enter to analyze.')
        self.input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        row.addWidget(self.input,1)
        self.submit=QPushButton(''); self.submit.setObjectName('primary'); self.submit.setIcon(icon('arrow-right','#282a27',20)); self.submit.setIconSize(QSize(20,20)); self.submit.setFixedSize(44,44); self.submit.setToolTip('Analyze link · Enter'); self.submit.setAccessibleName('Analyze link')
        row.addWidget(self.submit); outer.addLayout(row)
        self.busy=ProgressIndicator(); self.busy.setFixedHeight(4); self.busy.hide(); outer.addWidget(self.busy)
        self.input.textChanged.connect(lambda:self.source.detect(self.input.toPlainText()))
        self.input.submitted.connect(self.submitted); self.input.pasted.connect(self.submitted); self.submit.clicked.connect(self.submitted)
    def analyzing(self,value):
        self.busy.setVisible(value); self.busy.progress(0,value); self.submit.setEnabled(not value)
        self.setAccessibleDescription('Analyzing media' if value else 'Paste a media link')

class Navigation(GlassSurface):
    selected=Signal(int)
    names=('Home','Queue','Library','Settings')
    icons=('house','list-video','library','settings-2')
    def __init__(self,parent=None):
        super().__init__(parent,radius=24); self.setFixedSize(480,56)
        self.indicator=NavigationDot(self); self.indicator.setFixedSize(4,4); self.indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout=QHBoxLayout(self); layout.setContentsMargins(6,6,6,6); layout.setSpacing(2); self.buttons=[]
        for i,name in enumerate(self.names):
            b=NavigationButton(name,self); b.setIcon(icon(self.icons[i])); b.setIconSize(QSize(24,24)); b.setObjectName('nav'); b.setCheckable(True); b.setFixedHeight(44); b.setAccessibleName(name)
            b.clicked.connect(lambda checked=False,index=i:self.selected.emit(index)); layout.addWidget(b); self.buttons.append(b)
        self.index=0
    def select(self,index):
        self.index=index
        for i,b in enumerate(self.buttons): b.setChecked(i==index)
        Motion.animate(self.indicator,b'pos',self.indicator_position(index),'spring'); self.indicator.raise_()
    def indicator_position(self,index):
        from PySide6.QtCore import QPoint
        return QPoint(self.buttons[index].geometry().center().x()-2,self.height()-9)
    def resizeEvent(self,event):
        super().resizeEvent(event); QTimer.singleShot(0,lambda:self.indicator.move(self.indicator_position(self.index)))

class EmptyState(QWidget):
    def __init__(self,title,subtitle,parent=None):
        super().__init__(parent); box=QVBoxLayout(self); box.setContentsMargins(24,64,24,64); box.setSpacing(12)
        for text,name in ((title,'cardTitle'),(subtitle,'muted')):
            w=label(text,name,True); w.setAlignment(Qt.AlignmentFlag.AlignCenter); box.addWidget(w)

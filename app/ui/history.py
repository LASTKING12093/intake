from app.widgets.surfaces import Artwork,platform_badge
from app.utils.urls import source_name
import json
from pathlib import Path
from PySide6.QtCore import Qt,Signal,QFile,QThreadPool,QSize
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QScrollArea,QLineEdit,QDialog,QPlainTextEdit,QMessageBox,QFormLayout
from app.widgets.common import label,button,combo,open_path
from app.widgets.surfaces import GlassSurface,EmptyState,ContextMenu
from app.ui.motion import Motion
from app.ui.assets import icon
from app.services.process import run_hidden
from app.workers.task import Task

class HistoryPage(QWidget):
    again=Signal(dict)
    def __init__(self,history,thumbnails):
        super().__init__(); self.history=history; self.thumbnails=thumbnails; self.setObjectName('page')
        layout=QVBoxLayout(self); layout.setContentsMargins(32,32,32,24); layout.setSpacing(18)
        layout.addWidget(label('Library','title')); layout.addWidget(label('Taken in. Kept here.','muted'))
        controls=QHBoxLayout(); self.search=QLineEdit(); self.search.setPlaceholderText('Search your media…'); self.search.setAccessibleName('Search library'); controls.addWidget(self.search,1)
        self.kind=combo(['All','Music','Videos','Playlists','Failed']); self.kind.setAccessibleName('Filter library'); controls.addWidget(self.kind)
        self.sort=combo(['Newest first','Oldest first','Title A–Z']); self.sort.setAccessibleName('Sort library'); controls.addWidget(self.sort); layout.addLayout(controls)
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); layout.addWidget(self.scroll,1)
        self.search.textChanged.connect(self.refresh); self.kind.currentTextChanged.connect(self.refresh); self.sort.currentTextChanged.connect(self.refresh)
    def filtered_rows(self):
        query=self.search.text().casefold(); kind=self.kind.currentText(); rows=[]
        for row in self.history.rows():
            info=row.get('info',{}); music=row['options']['mode']=='Audio'
            if query not in (row['title']+' '+info.get('artist','')+' '+info.get('album','')).casefold(): continue
            if kind=='Music' and not music or kind=='Videos' and music or kind=='Playlists' and not info.get('playlist_title'): continue
            if kind=='Failed' and row['state']!='Failed': continue
            rows.append(row)
        if self.sort.currentText()=='Oldest first': rows.reverse()
        elif self.sort.currentText()=='Title A–Z': rows.sort(key=lambda r:r['title'].casefold())
        return rows
    def refresh(self,*args):
        content=QWidget(); layout=QVBoxLayout(content); layout.setContentsMargins(0,0,4,0); layout.setSpacing(10); rows=self.filtered_rows()
        if not rows: layout.addWidget(EmptyState('Room for what matters.','Your downloaded media will appear here.' if not self.search.text() else 'No media matches your search.'))
        for row in rows:
            card=GlassSurface(radius=14); outer=QHBoxLayout(card); outer.setContentsMargins(20,12,20,12); outer.setSpacing(14)
            thumb=Artwork(); thumb.setPixmap(icon('music-2' if row['options']['mode']=='Audio' else 'film',size=28).pixmap(28,28)); thumb.setFixedSize(52,52); thumb.setAlignment(Qt.AlignmentFlag.AlignCenter); self.thumbnails.load(row.get('thumbnail',''),thumb,52,52); outer.addWidget(thumb); outer.addWidget(platform_badge(row.get('info',{}).get('catalog') or source_name(row.get('url','')),20))
            details=QVBoxLayout(); details.setSpacing(5); title=label(row['title'],'cardTitle',True); details.addWidget(title)
            info=row.get('info',{}); suffix=Path(row.get('output','')).suffix.upper().lstrip('.') or row['options']['container']
            details.addWidget(label(' · '.join(filter(None,[info.get('artist',''),suffix,row['date'][:10],row['state'] if row['state']!='Completed' else ''])),'muted',True)); outer.addLayout(details,1)
            open_button=button('Open',lambda checked=False,r=row:open_path(r['output'],self),'quiet'); open_button.setEnabled(bool(row.get('output') and Path(row['output']).is_file())); outer.addWidget(open_button)
            more=button('',None,'quiet'); more.setIcon(icon('ellipsis')); more.setIconSize(QSize(24,24)); more.setFixedWidth(44); more.setAccessibleName('Actions for '+row['title']); more.clicked.connect(lambda checked=False,r=row,b=more:self.actions(r,b)); outer.addWidget(more); layout.addWidget(card)
        layout.addStretch(); previous=self.scroll.takeWidget()
        if previous: previous.deleteLater()
        self.scroll.setWidget(content); Motion.appear(content)
    def actions(self,row,anchor):
        menu=ContextMenu(self)
        if row.get('output'):
            menu.addAction('Reveal in folder',lambda:open_path(Path(row['output']).parent,self))
            menu.addAction('Move file to Recycle Bin',lambda:self.trash(row))
        menu.addAction('Metadata & details',lambda:self.metadata(row)); menu.addAction('Download again',lambda:self.again.emit(row)); menu.addSeparator(); menu.addAction('Remove library entry',lambda:self.remove_row(row)); self._menu=menu; menu.popup(anchor.mapToGlobal(anchor.rect().bottomLeft()))
    def remove_row(self,row): self.history.remove(row['id']); self.refresh()
    def trash(self,row):
        if QMessageBox.question(self,'Move to Recycle Bin?',f"Move {Path(row['output']).name} to the Recycle Bin?")!=QMessageBox.StandardButton.Yes: return
        result=QFile.moveToTrash(row['output']); success=result[0] if isinstance(result,tuple) else result
        if success: self.remove_row(row)
        else: QMessageBox.warning(self,'File kept','The file could not be moved to the Recycle Bin. It was kept in place.')
    def metadata(self,row):
        dialog=QDialog(self); dialog.setWindowTitle('Media details'); dialog.resize(620,480); layout=QVBoxLayout(dialog); layout.setContentsMargins(28,28,28,28); layout.setSpacing(20); layout.addWidget(label(row['title'],'cardTitle',True))
        info=row.get('info',{}); form=QFormLayout(); form.setSpacing(12)
        for name,value in [('Artist',info.get('artist') or info.get('channel')),('Album',info.get('album')),('Collection',info.get('playlist_title')),('Added',row['date'][:10]),('Format',Path(row.get('output','')).suffix.lstrip('.').upper() or row['options']['container']),('Source',info.get('matched_title') or row.get('url')),('File',row.get('output'))]:
            if value: form.addRow(name,label(str(value),'muted',True))
        layout.addLayout(form)
        text=QPlainTextEdit(); text.setReadOnly(True); text.setPlainText(json.dumps(row,indent=2,ensure_ascii=False)); text.hide(); layout.addWidget(text)
        more=button('Technical details',lambda:text.setVisible(not text.isVisible()),'quiet'); layout.addWidget(more); layout.addStretch(); layout.addWidget(button('Close',dialog.accept)); Motion.appear(dialog); dialog.exec(); dialog.deleteLater()

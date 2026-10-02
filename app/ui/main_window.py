from dataclasses import replace

from pathlib import Path

from PySide6.QtCore import Qt,QTimer

from PySide6.QtGui import QShortcut,QKeySequence

from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QStackedWidget,QScrollArea,QDialog

from app import __version__

from app.models.download import Options,State,ACTIVE

from app.services.config import Config

from app.services.runtime import Runtime

from app.services.history import History

from app.services.download import DownloadService

from app.services.thumbnails import Thumbnails

from app.dialogs.playlist import PlaylistDialog

from app.widgets.download_card import DownloadCard,QueueItem

from app.widgets.surfaces import BrandMark,Composer,Navigation,EmptyState,GlassSurface,DownloadButton,AmbientPage

from app.widgets.common import label,button,open_path

from app.ui.settings import SettingsPage

from app.ui.history import HistoryPage

from app.ui.theme import stylesheet

from app.ui.motion import Motion
from app.widgets.transition_stack import TransitionStack

from app.ui.assets import icon

from PySide6.QtCore import QSize

from app.utils.urls import parse_urls,source_name

from app.utils.paths import data_dir





class MainWindow(QMainWindow):

    def __init__(self,config=None):

        super().__init__(); self.config=config or Config()

        self.runtime=Runtime(self.config); self.history=History(); self.service=DownloadService(self.config,self.runtime,self.history,self); self.thumbnails=Thumbnails(self)

        self.cards={}; self.pending_options={}; self.close_requested=False; self.current_result=None; self.collection=None

        self.setWindowTitle('INTAKE — Universal Media Downloader'); self.resize(1160,800); self.setMinimumSize(860,620); self.setAcceptDrops(True)

        central=QWidget(); central.setObjectName('shell'); shell=QVBoxLayout(central); shell.setContentsMargins(0,0,0,0); shell.setSpacing(0)

        header=QWidget(); header.setObjectName('header'); header.setFixedHeight(100)

        top=QHBoxLayout(header); top.setContentsMargins(32,24,32,16); top.setSpacing(24)

        brand=QWidget(); brand.setFixedWidth(170); brand_row=QHBoxLayout(brand); brand_row.setContentsMargins(0,0,0,0); brand_row.setSpacing(12)

        brand_row.addWidget(BrandMark(32)); brand_row.addWidget(label('INTAKE','brand')); brand_row.addStretch(); top.addWidget(brand)

        top.addStretch(); self.navigation=Navigation(); self.navigation.selected.connect(self.show_page); top.addWidget(self.navigation); self.nav=self.navigation.buttons; top.addStretch()

        folder=button('',self.open_download_folder,'quiet'); folder.setIcon(icon('folder-open',size=22)); folder.setIconSize(QSize(22,22)); folder.setFixedWidth(44); folder.setToolTip('Open downloads · Ctrl+Shift+O'); folder.setAccessibleName('Open downloads folder'); top.addWidget(folder)

        shell.addWidget(header)

        self.pages=TransitionStack(); shell.addWidget(self.pages,1)

        self.pages.addWidget(self.make_home()); self.pages.addWidget(self.make_queue())

        self.history_page=HistoryPage(self.history,self.thumbnails); self.history_page.again.connect(self.download_again); self.pages.addWidget(self.history_page)

        self.settings_page=SettingsPage(self.config,self.runtime,self.service); self.settings_page.theme_changed.connect(self.apply_theme); self.settings_page.folder_changed.connect(lambda _:self.update_folder_label()); self.pages.addWidget(self.settings_page)

        self.setCentralWidget(central); self.apply_theme('Dark')

        self.service.added.connect(self.add_card); self.service.changed.connect(self.refresh_card); self.service.removed.connect(self.remove_card)

        self.service.info_ready.connect(self.received_info); self.service.info_failed.connect(self.info_failed); self.service.activity.connect(self.update_counts)

        self.restoring=True; self.service.restore_queue(); self.restoring=False

        self.show_page({'Queue':1,'Library':2,'History':2,'Settings':3}.get(self.config.get('launch_behavior'),0)); self.update_counts()

        for seq,callback in [('Ctrl+L',lambda:(self.show_page(0),self.url.setFocus())),('Ctrl+,',lambda:self.show_page(3)),('Ctrl+Shift+O',self.open_download_folder),('Ctrl+1',lambda:self.show_page(0)),('Ctrl+2',lambda:self.show_page(1)),('Ctrl+3',lambda:self.show_page(2))]: QShortcut(QKeySequence(seq),self,activated=callback)

        self.paste_shortcut=QShortcut(QKeySequence('Ctrl+V'),self,activated=self.paste_links)



    def make_home(self):

        page=AmbientPage(); outer=QVBoxLayout(page); outer.setContentsMargins(32,24,32,24)

        self.home_scroll=QScrollArea(); self.home_scroll.setWidgetResizable(True); self.home_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content=QWidget(); content_box=QVBoxLayout(content); content_box.setContentsMargins(0,0,0,0); content_box.addStretch(2)

        align=QHBoxLayout(); align.addStretch(); self.home_center=QWidget(); self.home_center.setMaximumWidth(800); column=QVBoxLayout(self.home_center); column.setContentsMargins(2,20,2,20); column.setSpacing(28)

        self.hero=QWidget(); hero=QVBoxLayout(self.hero); hero.setContentsMargins(4,0,0,4); hero.setSpacing(12)

        hero.addWidget(label('Anything in.','homeHeading'))

        hero.addWidget(label('Take it in. Keep it yours.','tagline'))

        column.addWidget(self.hero)

        self.composer=Composer(); self.composer.submitted.connect(self.add_links); self.url=self.composer.input; self.add_button=self.composer.submit; column.addWidget(self.composer)

        self.platform_hint=label('YouTube, TikTok, Spotify, Apple Music and more.','platformHint'); self.platform_hint.setAlignment(Qt.AlignmentFlag.AlignLeft); column.addWidget(self.platform_hint)

        self.message=label('','status',True); self.message.hide(); column.addWidget(self.message)

        self.error_actions=QWidget(); errors=QHBoxLayout(self.error_actions); errors.setContentsMargins(0,0,0,0)

        errors.addWidget(button('Try again',self.add_links,'quiet')); errors.addWidget(button('Refresh extractor',self.refresh_engine,'quiet')); errors.addWidget(button('Details',lambda:open_path(data_dir()/'logs',self),'quiet')); errors.addStretch(); self.error_actions.hide(); column.addWidget(self.error_actions)

        self.result_host=QWidget(); self.result_layout=QVBoxLayout(self.result_host); self.result_layout.setContentsMargins(0,0,0,0); self.result_host.hide(); column.addWidget(self.result_host)

        self.queue_hint=button('',lambda:self.show_page(1),'quiet'); self.queue_hint.hide(); column.addWidget(self.queue_hint)

        align.addWidget(self.home_center,1); align.addStretch(); content_box.addLayout(align); content_box.addStretch(3); self.home_scroll.setWidget(content); outer.addWidget(self.home_scroll)

        return page



    def make_queue(self):

        page=QWidget(); page.setObjectName('page'); layout=QVBoxLayout(page); layout.setContentsMargins(32,32,32,24); layout.setSpacing(20)

        layout.addWidget(label('Queue','title')); self.queue_title=label('Everything in motion.','muted'); layout.addWidget(self.queue_title)

        toolbar=QHBoxLayout(); toolbar.addWidget(button('Start all',self.start_all,'quiet')); self.pause_all_button=button('Pause all',self.toggle_pause_all,'quiet'); toolbar.addWidget(self.pause_all_button); toolbar.addWidget(button('Cancel all',self.service.cancel_all,'quiet')); toolbar.addStretch(); toolbar.addWidget(button('Clear completed',self.clear_completed,'quiet')); layout.addLayout(toolbar)

        self.queue_scroll=QScrollArea(); self.queue_scroll.setWidgetResizable(True); self.queue_content=QWidget(); self.queue_layout=QVBoxLayout(self.queue_content); self.queue_layout.setContentsMargins(0,0,4,0); self.queue_layout.setSpacing(10)

        self.empty=EmptyState('Nothing in motion.','Paste a link on Home. Your downloads will appear here.'); self.queue_layout.addWidget(self.empty); self.queue_layout.addStretch(); self.queue_scroll.setWidget(self.queue_content); layout.addWidget(self.queue_scroll,1)

        self.folder_label=button('',self.open_download_folder,'quiet'); self.update_folder_label(); layout.addWidget(self.folder_label,0,Qt.AlignmentFlag.AlignLeft)

        return page



    def current_options(self,info=None):

        info=info or {}; music=bool(info.get('catalog')); smart=self.config.get('smart_defaults')

        return Options(mode='Audio' if music else 'Video',container=('Original / Best Audio' if smart else self.config.get('audio_format')) if music else ('Auto' if smart else self.config.get('video_container')),

            quality='Best' if smart else self.config.get('audio_bitrate' if music else 'video_quality'),metadata=self.config.get('metadata'),thumbnail=True if music else self.config.get('thumbnails'),lyrics=self.config.get('lyrics'))



    def notify(self,text): self.message.setText(text); self.message.setVisible(bool(text))

    def add_links(self):

        urls=parse_urls(self.url.toPlainText())

        if not urls: self.notify('Paste a media link to get started.'); return

        self.show_page(0); self.error_actions.hide()

        selected=self.composer.source.manual

        if selected!='Auto Detect' and any(source_name(url)!=selected for url in urls):

            self.notify(f'This link is not from {selected}. Choose Auto Detect to recognize it automatically.'); return

        pending=[]

        for url in urls:

            existing=next((j for j in self.service.jobs.values() if j.url==url and j.state not in {State.CANCELLED,State.FAILED}),None)

            if existing: self.show_result(existing); continue

            if url not in self.pending_options:

                self.pending_options[url]=None; pending.append(url)

        if pending:

            self.composer.analyzing(True); self.notify('Understanding your link…' if len(pending)==1 else f'Understanding {len(pending)} links…')

            for url in pending: self.service.get_info(url)



    def received_info(self,url,info):

        if self.close_requested: return

        options=self.pending_options.pop(url,None) or self.current_options(info)

        if 'entries' in info: self.show_collection(url,info,options)

        else: self.service.add(url,info,options)

        self.composer.analyzing(bool(self.pending_options)); self.notify('Understanding remaining links…' if self.pending_options else '')

    def info_failed(self,url,error):

        self.pending_options.pop(url,None); self.composer.analyzing(bool(self.pending_options))

        if not self.close_requested: self.notify(error); self.error_actions.show()

    def clear_result(self):

        while self.result_layout.count():

            item=self.result_layout.takeAt(0)

            if item.widget(): item.widget().deleteLater()

        self.current_result=None

    def show_result(self,job):

        was_visible=self.result_host.isVisible(); self.clear_result(); card=DownloadCard(job,self.service,self.thumbnails); self.current_result=card; self.result_layout.addWidget(card); self.result_host.show(); self.platform_hint.hide(); Motion.appear(card)

        if not was_visible: Motion.expand(self.result_host,True)

    def show_collection(self,url,info,options):

        self.clear_result(); self.collection=(url,info,options)

        card=GlassSurface(); box=QVBoxLayout(card); box.setContentsMargins(24,24,24,24); box.setSpacing(14)

        box.addWidget(label(info.get('title','Collection'),'cardTitle',True)); box.addWidget(label(f"{info.get('catalog') or source_name(url)} · {len([e for e in info['entries'] if e])} items",'muted'))

        if info.get('collection_notice'): box.addWidget(label(info['collection_notice'],'muted',True))

        row=QHBoxLayout(); row.addWidget(label('Best Available','status')); row.addStretch(); row.addWidget(DownloadButton('Choose items',self.select_collection)); box.addLayout(row)

        self.result_layout.addWidget(card); self.result_host.show(); self.platform_hint.hide(); Motion.appear(card)

    def select_collection(self):

        url,info,options=self.collection; dialog=PlaylistDialog(info,self.thumbnails,self)

        if dialog.exec()==QDialog.DialogCode.Accepted:

            for index,entry in dialog.selected():

                entry=dict(entry,playlist_title=info.get('title',''),playlist_index=entry.get('playlist_index') or index)

                entry_url=entry.get('webpage_url') or entry.get('url') or 'https://www.youtube.com/watch?v='+entry.get('id','')

                valid=parse_urls(entry_url)

                if not valid: continue

                if any(j.url==valid[0] and j.state not in {State.CANCELLED,State.FAILED} for j in self.service.jobs.values()): continue

                self.batch_adding=True

                job=self.service.add(valid[0],entry,replace(options)); self.service.enqueue(job)

                self.batch_adding=False

            self.show_page(1)

        dialog.deleteLater()

    def add_card(self,job):

        item=QueueItem(job,self.service,self.thumbnails); item.inspect.connect(lambda j:(self.show_result(j),self.show_page(0))); self.cards[job.id]=item; self.queue_layout.insertWidget(self.queue_layout.count()-1,item)

        Motion.appear(item); Motion.expand(item,True)

        if not getattr(self,'restoring',False) and not getattr(self,'batch_adding',False): self.show_result(job)

        self.update_counts()

    def refresh_card(self,job):

        if job.id in self.cards: self.cards[job.id].refresh()

        if self.current_result and self.current_result.job.id==job.id: self.current_result.refresh()

        self.update_counts()

    def remove_card(self,job_id):

        card=self.cards.pop(job_id,None)

        if card:

            Motion.animate(card,b'maximumHeight',0,'layout',start=card.height(),finished=card.deleteLater)

        if self.current_result and self.current_result.job.id==job_id:

            self.clear_result(); self.result_host.hide(); self.platform_hint.show()

        self.update_counts()

    def update_counts(self):

        if not hasattr(self,'empty'): return

        self.empty.setVisible(not self.cards); active=sum(j.state in ACTIVE|{State.WAITING,State.PAUSED} for j in self.service.jobs.values())

        self.queue_title.setText(f'{len(self.cards)} items · {len(self.service.active)} active' if self.cards else 'Everything in motion.')

        self.nav[1].setText('Queue'+(f'  {active}' if active else ''))

        self.queue_hint.setText(f'{active} in queue  ·  View activity'); self.queue_hint.setVisible(active>0)

        self.pause_all_button.setText('Resume all' if self.service.queue_paused else 'Pause all')

        if self.close_requested and not self.service.active and not self.service.inspectors and not self.service.maintenance: QTimer.singleShot(0,self.close)

    def start_all(self):

        self.service.resume_all()

        for job in self.service.jobs.values():

            if job.state==State.READY: self.service.enqueue(job)

    def toggle_pause_all(self):

        self.service.resume_all() if self.service.queue_paused else self.service.pause_all(); self.update_counts()

    def clear_completed(self):

        for job in list(self.service.jobs.values()):

            if job.state==State.COMPLETED: self.service.remove(job)

    def show_page(self,index):
        if index==2: self.history_page.refresh()
        self.pages.setCurrentIndex(index); self.navigation.select(index)

    def apply_theme(self,theme): QApplication.instance().setStyleSheet(stylesheet(theme))

    def update_folder_label(self):

        if hasattr(self,'folder_label'):

            path=self.config.get('download_folder'); self.folder_label.setText('Saving to  '+Path(path).name); self.folder_label.setIcon(icon('folder-open',size=18)); self.folder_label.setToolTip(path)

    def open_download_folder(self):

        try:

            path=Path(self.config.get('download_folder')); path.mkdir(parents=True,exist_ok=True); open_path(path,self)

        except OSError: self.notify('Cannot open this folder. Choose another location in Settings.')

    def refresh_engine(self): self.show_page(3); self.settings_page.update_engine()

    def paste_links(self):

        focus=QApplication.focusWidget()

        if focus and focus is not self.url and hasattr(focus,'paste'): focus.paste(); return

        text=QApplication.clipboard().text()

        if parse_urls(text): self.url.setPlainText(text); self.add_links()

        else: self.url.insertPlainText(text)

    def dragEnterEvent(self,event):

        if event.mimeData().hasText() and parse_urls(event.mimeData().text()): event.acceptProposedAction()

    def dropEvent(self,event):

        self.url.setPlainText(event.mimeData().text()); self.add_links(); event.acceptProposedAction()

    def download_again(self,row):

        self.show_page(0); self.url.setPlainText(row['url']); self.pending_options[row['url']]=Options(**row['options']); self.composer.analyzing(True); self.service.get_info(row['url']); self.notify('Refreshing media information…')

    def closeEvent(self,event):

        if self.service.active or self.service.inspectors or self.service.maintenance:

            self.close_requested=True; self.service.shutdown(); self.notify('Keeping partial files and closing safely…'); event.ignore()

        else: self.service.save_queue(); event.accept()


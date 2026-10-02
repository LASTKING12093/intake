from app.widgets.surfaces import Artwork,platform_badge
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QFormLayout,QCheckBox,QLineEdit,QFileDialog,QMessageBox
from app.widgets.common import label,button,combo,duration,size_text,open_path
from app.widgets.surfaces import GlassSurface,DownloadButton,ProgressIndicator,ContextMenu
from app.ui.motion import Motion
from app.ui.assets import icon
from app.services.formats import VIDEO_FORMATS,AUDIO_FORMATS,resolutions
from app.models.download import State,ACTIVE
from app.utils.urls import source_name


def primary_action(job,service,parent):
    if job.state==State.COMPLETED: open_path(job.output,parent)
    elif job.state in ACTIVE|{State.WAITING}: service.pause(job)
    else: service.enqueue(job)


def action_text(state):
    return {State.READY:'Download',State.PAUSED:'Resume',State.COMPLETED:'Open file',State.FAILED:'Retry',State.CANCELLED:'Retry'}.get(state,'Pause')


class DownloadCard(GlassSurface):
    """One contextual media result; it remains the same object through completion."""
    def __init__(self,job,service,thumbnails):
        super().__init__(); self.job=job; self.service=service; self.opened=False
        layout=QVBoxLayout(self); layout.setContentsMargins(24,24,24,22); layout.setSpacing(16)
        top=QHBoxLayout(); top.setSpacing(18)
        thumb=Artwork(); thumb.setPixmap(icon('music-2' if job.options.mode=='Audio' else 'film',size=28).pixmap(28,28)); thumb.setAlignment(Qt.AlignmentFlag.AlignCenter); thumb.setFixedSize(80,80)
        thumbnails.load(job.info.get('thumbnail',''),thumb,80,80); top.addWidget(thumb)
        details=QVBoxLayout(); details.setSpacing(6)
        self.title_label=label(job.title,'cardTitle',True); details.addWidget(self.title_label)
        artist=job.info.get('artist') or job.info.get('channel') or job.info.get('uploader','')
        details.addWidget(label(artist,'muted',True))
        source=job.info.get('catalog') or source_name(job.url)
        source_row=QHBoxLayout(); source_row.setSpacing(8); source_row.addWidget(platform_badge(source))
        self.source_label=label(source+'  ·  '+duration(job.info.get('duration')),'muted'); source_row.addWidget(self.source_label); source_row.addStretch(); details.addLayout(source_row)
        top.addLayout(details,1); layout.addLayout(top)
        self.match=None
        if job.info.get('match_candidates'):
            self.match=combo([])
            for candidate in job.info['match_candidates']:
                self.match.addItem(f"{candidate['title']} · {candidate['channel']} · {duration(candidate['duration'])}",candidate)
            match_row=QVBoxLayout(); match_row.addWidget(label('Audio source · YouTube match — review the recording','muted',True)); match_row.addWidget(self.match)
            layout.addLayout(match_row); self.match.currentIndexChanged.connect(self.match_changed)
            self.match.setAccessibleName('Matched audio recording. Choose the correct source.')
        self.match_confirm=QCheckBox('This is the recording I want')
        self.match_confirm.setVisible(bool(job.info.get('catalog') and job.info.get('match_score',1)<.78))
        self.match_confirm.setChecked(bool(job.info.get('match_approved')))
        self.match_confirm.toggled.connect(self.approve_match); layout.addWidget(self.match_confirm)
        action_row=QHBoxLayout(); action_row.setSpacing(8)
        self.mode=combo(['Audio'] if job.info.get('catalog') else ['Video','Audio'],job.options.mode)
        self.mode.setMaximumWidth(100); self.mode.setAccessibleName('Media type'); action_row.addWidget(self.mode)
        self.quality_hint=button('Best Available',self.toggle_options,'quiet'); action_row.addWidget(self.quality_hint); action_row.addStretch()
        self.options_button=button('Options',self.toggle_options,'quiet'); action_row.addWidget(self.options_button)
        self.action=DownloadButton('Download',self.primary_action); action_row.addWidget(self.action); layout.addLayout(action_row)
        self.advanced=QWidget(); form=QFormLayout(self.advanced); form.setContentsMargins(0,8,0,8); form.setSpacing(12); form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.container=combo(VIDEO_FORMATS if job.options.mode=='Video' else AUDIO_FORMATS,job.options.container)
        self.quality=combo(['Best']); self._qualities(); self.quality.setCurrentText(job.options.quality)
        self.video_codec=combo(['Auto','H.264','VP9','AV1'],job.options.video_codec)
        self.audio_codec=combo(['Auto','AAC','Opus'],job.options.audio_codec)
        self.metadata=QCheckBox('Preserve title, artist and tags'); self.metadata.setChecked(job.options.metadata)
        self.artwork=QCheckBox('Keep artwork'); self.artwork.setChecked(job.options.thumbnail)
        self.lyrics=QCheckBox('Save lyrics when available (.lrc / .txt)'); self.lyrics.setChecked(job.options.lyrics)
        self.subtitle=combo([]); self.subtitle.addItem('Off',('',False))
        for auto,key in ((False,'subtitles'),(True,'automatic_captions')):
            for lang in sorted(job.info.get(key,{})):
                self.subtitle.addItem(('Automatic · ' if auto else '')+lang,(lang,auto))
        for i in range(self.subtitle.count()):
            if self.subtitle.itemData(i)==(job.options.subtitle,job.options.auto_subtitle): self.subtitle.setCurrentIndex(i)
        self.subtitle_mode=combo(['Embed into video','Download .srt separately'],job.options.subtitle_mode)
        self.filename=QLineEdit(job.options.filename); self.filename.setPlaceholderText('Automatic · '+job.title)
        self.destination=QLineEdit(job.destination)
        location=QHBoxLayout(); location.addWidget(self.destination); location.addWidget(button('Browse',self.choose_destination))
        for name,field in [('Format',self.container),('Quality',self.quality),('Video codec',self.video_codec),('Source audio codec',self.audio_codec),('Subtitles',self.subtitle),('Subtitle delivery',self.subtitle_mode),('Metadata',self.metadata),('Artwork',self.artwork),('Lyrics',self.lyrics),('Filename',self.filename),('Save to',location)]:
            form.addRow(name,field)
            if isinstance(field,QWidget): field.setAccessibleName(name)
        self.form=form
        self.note=label('','muted',True); form.addRow(self.note)
        layout.addWidget(self.advanced); self.advanced.hide()
        self.bar=ProgressIndicator(); layout.addWidget(self.bar)
        status_row=QHBoxLayout(); self.completion_icon=label(''); self.completion_icon.setPixmap(icon('check',size=20).pixmap(20,20)); self.completion_icon.setFixedSize(20,20); self.completion_icon.hide(); status_row.addWidget(self.completion_icon); self.status=label('','status'); status_row.addWidget(self.status); status_row.addStretch()
        self.cancel_btn=button('Cancel',lambda:service.cancel(job),'quiet'); status_row.addWidget(self.cancel_btn)
        self.folder_btn=button('Reveal',lambda:open_path(Path(job.output).parent,self),'quiet'); status_row.addWidget(self.folder_btn)
        layout.addLayout(status_row)
        self.stats=label('','muted',True); layout.addWidget(self.stats)
        self.mode.currentTextChanged.connect(self._mode_changed); self.container.currentTextChanged.connect(self._container_changed)
        for field in (self.quality,self.video_codec,self.audio_codec,self.subtitle,self.subtitle_mode): field.currentIndexChanged.connect(self._save_options)
        for field in (self.metadata,self.artwork,self.lyrics): field.toggled.connect(self._save_options)
        self.filename.editingFinished.connect(self._save_options); self.destination.editingFinished.connect(self._save_options)
        self.refresh()

    def choose_destination(self):
        folder=QFileDialog.getExistingDirectory(self,'Save media to',self.destination.text())
        if folder: self.destination.setText(folder); self._save_options()
    def toggle_options(self):
        self.opened=not self.opened; self.options_button.setText('Less' if self.opened else 'Options'); Motion.expand(self.advanced,self.opened)
    def _qualities(self):
        previous=self.quality.currentText(); self.quality.clear()
        if self.mode.currentText()=='Video': self.quality.addItems(resolutions(self.job.info,self.container.currentText()))
        elif self.container.currentText()=='MP3': self.quality.addItems(['Best','320 kbps','256 kbps','192 kbps','128 kbps'])
        else: self.quality.addItem('PCM' if self.container.currentText()=='WAV' else 'Best')
        if self.quality.findText(previous)>=0: self.quality.setCurrentText(previous)
    def _mode_changed(self):
        self.container.blockSignals(True); self.container.clear(); self.container.addItems(VIDEO_FORMATS if self.mode.currentText()=='Video' else AUDIO_FORMATS); self.container.blockSignals(False); self._container_changed()
    def _container_changed(self):
        self.quality.blockSignals(True); self._qualities(); self.quality.blockSignals(False); self._save_options()
    def _save_options(self):
        if not self.quality.currentText(): return
        opts=self.job.options
        opts.mode,opts.container,opts.quality=self.mode.currentText(),self.container.currentText(),self.quality.currentText()
        opts.video_codec,opts.audio_codec=self.video_codec.currentText(),self.audio_codec.currentText()
        opts.metadata,opts.thumbnail,opts.lyrics=self.metadata.isChecked(),self.artwork.isChecked(),self.lyrics.isChecked()
        opts.subtitle,opts.auto_subtitle=self.subtitle.currentData() or ('',False); opts.subtitle_mode=self.subtitle_mode.currentText()
        opts.filename=self.filename.text().strip(); self.job.destination=self.destination.text().strip() or self.service.config.get('download_folder')
        self.service.save_queue(); self.refresh()
    def match_changed(self):
        candidate=self.match.currentData()
        self.job.info.update(source_url=candidate['url'],matched_title=candidate['title'],matched_channel=candidate['channel'],match_score=candidate['score'])
        self.match_confirm.setVisible(candidate['score']<.78); self.match_confirm.setChecked(False); self.service.save_queue(); self.refresh()
    def approve_match(self,approved):
        self.job.info['match_approved']=approved; self.service.save_queue(); self.refresh()
    def primary_action(self):
        if self.job.state in {State.READY,State.FAILED,State.CANCELLED}: self._save_options()
        if self.opened: self.toggle_options()
        primary_action(self.job,self.service,self)
    def refresh(self):
        job=self.job; opts=job.options; audio=opts.mode=='Audio'; editable=job.state in {State.READY,State.FAILED,State.CANCELLED}
        self.advanced.setEnabled(editable); self.mode.setEnabled(editable)
        if self.match: self.match.setEnabled(editable)
        self.match_confirm.setEnabled(editable)
        for field,visible in ((self.video_codec,not audio),(self.subtitle,not audio and self.subtitle.count()>1),(self.subtitle_mode,not audio and bool(opts.subtitle)),(self.artwork,audio),(self.lyrics,audio and bool(job.info.get('artist')))):
            self.form.setRowVisible(field,visible)
        self.mode.setVisible(not bool(job.info.get('catalog')))
        quality='Best Available' if opts.quality in {'Best','PCM'} else opts.quality
        detail=opts.container if opts.container not in {'Auto',AUDIO_FORMATS[0]} else ''
        if not audio and opts.quality=='Best':
            height=max((f.get('height') or 0 for f in job.info.get('formats',[])),default=0)
            if height: detail='4K' if height==2160 else '8K' if height==4320 else str(height)+'p'
        self.quality_hint.setText(quality+('  ·  '+detail if detail else ''))
        self.action.setText(action_text(job.state)); self.action.setAccessibleName(action_text(job.state)); self.folder_btn.setIcon(icon('folder-open',size=18))
        stopping=job.id in self.service.active and self.service.active[job.id][1] is not None
        uncertain=bool(job.info.get('catalog') and job.info.get('match_score',1)<.78)
        self.action.setEnabled(not stopping and (not uncertain or self.match_confirm.isChecked()))
        self.cancel_btn.setVisible(job.state in ACTIVE|{State.WAITING,State.PAUSED,State.FAILED}); self.cancel_btn.setEnabled(not stopping)
        self.folder_btn.setVisible(job.state==State.COMPLETED)
        self.status.setText('Yours offline' if job.state==State.COMPLETED else '' if job.state==State.READY else str(job.state))
        self.status.setVisible(job.state!=State.READY)
        was_complete=self.completion_icon.isVisible(); self.completion_icon.setVisible(job.state==State.COMPLETED)
        if job.state==State.COMPLETED and not was_complete: Motion.appear(self.completion_icon)
        self.bar.setVisible(job.state in ACTIVE|{State.PAUSED})
        self.bar.progress(job.progress,job.state in {State.INFO,State.PROCESSING,State.CONVERTING})
        stats=job.error
        if job.state==State.DOWNLOADING: stats=f'{job.progress:.0f}%  ·  {size_text(job.total*job.progress/100)} / {size_text(job.total)}  ·  {size_text(job.speed)}/s'
        elif job.state==State.COMPLETED: stats=Path(job.output).name
        elif job.state==State.PAUSED: stats='Partial files kept. Resume continues where the source supports it.'
        elif job.state in {State.PROCESSING,State.CONVERTING}: stats='Preparing your file…'
        self.stats.setText(stats); self.stats.setVisible(bool(stats))
        self.note.setText('Best source, without unnecessary transcoding. Artwork is saved separately if the original format cannot embed it.' if audio and opts.container==AUDIO_FORMATS[0] else 'Auto keeps the best streams; separate video and audio are combined in MKV.' if not audio and opts.container=='Auto' else 'Codec filters select source streams. Unavailable combinations fail rather than silently reducing quality.')


class QueueItem(GlassSurface):
    inspect=Signal(object)
    def __init__(self,job,service,thumbnails):
        super().__init__(radius=14); self.job=job; self.service=service
        outer=QVBoxLayout(self); outer.setContentsMargins(20,12,20,12); outer.setSpacing(8)
        row=QHBoxLayout(); row.setSpacing(14)
        thumb=Artwork(); thumb.setPixmap(icon('music-2' if job.options.mode=='Audio' else 'film',size=28).pixmap(28,28)); thumb.setFixedSize(48,48); thumb.setAlignment(Qt.AlignmentFlag.AlignCenter); thumbnails.load(job.info.get('thumbnail',''),thumb,48,48); row.addWidget(thumb); row.addWidget(platform_badge(job.info.get('catalog') or source_name(job.url),20))
        detail=QVBoxLayout(); detail.setSpacing(4); self.title_label=label(job.title,'cardTitle'); detail.addWidget(self.title_label); self.status=label('','muted'); detail.addWidget(self.status); row.addLayout(detail,1)
        self.action=button('Download',self.primary_action,'quiet'); row.addWidget(self.action)
        menu_button=button('',self.menu,'quiet'); menu_button.setIcon(icon('ellipsis')); menu_button.setIconSize(QSize(24,24)); menu_button.setFixedWidth(44); menu_button.setAccessibleName('Actions for '+job.title); row.addWidget(menu_button); self.menu_button=menu_button
        outer.addLayout(row); self.bar=ProgressIndicator(); outer.addWidget(self.bar); self.refresh()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.customContextMenuRequested.connect(lambda _:self.menu())
    def primary_action(self): primary_action(self.job,self.service,self)
    def menu(self):
        menu=ContextMenu(self); menu.addAction('Inspect / Options',lambda:self.inspect.emit(self.job))
        if self.job.output: menu.addAction('Reveal in folder',lambda:open_path(Path(self.job.output).parent,self))
        if self.job.state not in {State.COMPLETED,State.CANCELLED}: menu.addAction('Cancel download',lambda:self.service.cancel(self.job))
        remove=menu.addAction('Remove from queue',lambda:self.service.remove(self.job)); remove.setEnabled(self.job.id not in self.service.active)
        menu.popup(self.menu_button.mapToGlobal(self.menu_button.rect().bottomLeft())); self._menu=menu
    def refresh(self):
        job=self.job; title=self.fontMetrics().elidedText(job.title,Qt.TextElideMode.ElideRight,max(100,self.width()-270)); self.title_label.setText(title); self.title_label.setToolTip(job.title)
        text='Completed' if job.state==State.COMPLETED else str(job.state)
        if job.state==State.DOWNLOADING: text+=f'  ·  {job.progress:.0f}%  ·  {size_text(job.speed)}/s'
        self.status.setText(text); self.status.setToolTip(job.error)
        self.action.setText(action_text(job.state)); self.action.setEnabled(not (job.id in self.service.active and self.service.active[job.id][1] is not None))
        self.bar.setVisible(job.state in ACTIVE|{State.PAUSED}); self.bar.progress(job.progress,job.state in {State.INFO,State.PROCESSING,State.CONVERTING})
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'status'): self.refresh()

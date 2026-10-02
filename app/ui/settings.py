from shiboken6 import isValid
from PySide6.QtCore import Signal,QThreadPool
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QSpinBox,QCheckBox,QFileDialog,QScrollArea
from app import __version__
from app.widgets.common import label,button,combo,open_path
from app.widgets.surfaces import GlassSurface
from app.services.formats import VIDEO_FORMATS,AUDIO_FORMATS
from app.services.ffmpeg import FFmpegService
from app.workers.task import Task
from app.ui.motion import Motion
from app.utils.paths import data_dir

class SettingsPage(QWidget):
    theme_changed=Signal(str)
    folder_changed=Signal(str)
    def __init__(self,config,runtime,service):
        super().__init__(); self.config=config; self.runtime=runtime; self.service=service; self.setObjectName('page')
        outer=QVBoxLayout(self); outer.setContentsMargins(32,32,32,24); outer.setSpacing(16)
        outer.addWidget(label('Settings','title')); outer.addWidget(label('Thoughtful defaults. A few things to make yours.','muted'))
        scroll=QScrollArea(); scroll.setWidgetResizable(True); content=QWidget(); layout=QVBoxLayout(content); layout.setContentsMargins(0,8,4,0); layout.setSpacing(14)
        def group(title,opened=False):
            surface=GlassSurface(radius=14); box=QVBoxLayout(surface); box.setContentsMargins(16,8,16,12)
            toggle=button(title+('  −' if opened else '  +'),None,'quiet'); toggle.setStyleSheet('text-align:left;'); box.addWidget(toggle)
            body=QWidget(); form=QFormLayout(body); form.setSpacing(12); form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows); form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            box.addWidget(body); body.setVisible(opened); toggle.setCheckable(True); toggle.setChecked(opened)
            toggle.toggled.connect(lambda checked:(toggle.setText(title+('  −' if checked else '  +')),Motion.expand(body,checked)))
            layout.addWidget(surface); return form
        general=group('Downloads',True)
        self.folder_edit=self.path_field(general,'Save to','download_folder')
        concurrent=QSpinBox(); concurrent.setRange(1,5); concurrent.setValue(config.get('concurrent')); concurrent.valueChanged.connect(lambda v:(config.set('concurrent',v),service._pump())); general.addRow('At the same time',concurrent)
        appearance=group('Appearance & behavior')
        self.select_field(appearance,'Open on launch','launch_behavior',['Home','Queue','Library'])
        quality=group('Quality & enrichment')
        smart=QCheckBox('Choose the best available quality automatically'); smart.setChecked(config.get('smart_defaults')); smart.toggled.connect(lambda v:config.set('smart_defaults',v)); quality.addRow(smart)
        self.select_field(quality,'Video format','video_container',VIDEO_FORMATS)
        self.select_field(quality,'Video resolution','video_quality',['Best','2160p','1440p','1080p','720p','480p','360p'])
        self.select_field(quality,'Audio format','audio_format',AUDIO_FORMATS)
        self.select_field(quality,'MP3 bitrate','audio_bitrate',['Best','320 kbps','256 kbps','192 kbps','128 kbps'])
        quality.addRow(label('Manual defaults apply when automatic quality is off. A higher bitrate cannot restore detail missing from a source.','muted',True))
        for key,text in [('metadata','Preserve metadata'),('thumbnails','Keep artwork for audio extraction'),('lyrics','Save lyrics for identified music when available')]:
            check=QCheckBox(text); check.setChecked(config.get(key)); check.toggled.connect(lambda value,k=key:config.set(k,value)); quality.addRow(check)
        updates=group('Download engine',True)
        self.update_status=label('Keep site compatibility up to date. Updates are verified before installation.','muted',True); updates.addRow(self.update_status)
        row=QHBoxLayout(); self.check_button=button('Check for updates',self.check_updates); self.update_button=button('Refresh engine',self.update_engine,'primary'); row.addWidget(self.check_button); row.addWidget(self.update_button); row.addStretch(); updates.addRow(row)
        advanced=group('Advanced')
        self.path_field(advanced,'Extractor executable','yt_dlp_path',file=True,placeholder=str(runtime.yt_dlp()))
        self.path_field(advanced,'FFmpeg folder','ffmpeg_path',placeholder=str(runtime.ffmpeg_dir()))
        self.path_field(advanced,'Temporary folder','temp_folder',placeholder='Automatic')
        self.engine_version=label('Checking…','muted',True); self.ffmpeg_version=label('Checking…','muted',True)
        advanced.addRow('Extractor version',self.engine_version); advanced.addRow('FFmpeg version',self.ffmpeg_version)
        advanced.addRow(button('Open diagnostic logs',lambda:open_path(data_dir()/'logs',self),'quiet'))
        layout.addWidget(label('INTAKE '+__version__+'  ·  Universal Media Downloader','muted'))
        layout.addWidget(label('Download media you own or have permission to keep. Catalog links identify recordings; audio comes from the compatible source shown in the result.','muted',True))
        layout.addStretch(); scroll.setWidget(content); outer.addWidget(scroll); self.refresh_versions()

    def select_field(self, form, title, key, values):
        field = combo(values, self.config.get(key))
        field.currentTextChanged.connect(lambda value: self.config.set(key, value))
        form.addRow(title, field)
        return field

    def path_field(self, form, title, key, file=False, placeholder=""):
        row = QHBoxLayout()
        field = QLineEdit(self.config.get(key))
        field.setPlaceholderText(placeholder)
        def save():
            self.config.set(key, field.text().strip())
            if key == "download_folder":
                self.folder_changed.emit(field.text().strip())
        field.editingFinished.connect(save)
        def choose():
            path = QFileDialog.getOpenFileName(self, title, field.text(), "Executable (*.exe)")[0] if file else QFileDialog.getExistingDirectory(self, title, field.text())
            if path:
                field.setText(path)
                save()
        row.addWidget(field)
        row.addWidget(button("Browse", choose))
        form.addRow(title, row)
        return field

    def run_task(self, function, callback):
        task = Task(function)
        task.signals.result.connect(lambda result: callback(result) if isValid(self) else None)
        task.signals.error.connect(lambda error: self.update_status.setText("Could not complete this action. Check your connection and runtime paths. Details are in the log.") if isValid(self) else None)
        task.signals.finished.connect(lambda: (self.check_button.setEnabled(True), self.update_button.setEnabled(True)) if isValid(self) else None)
        self.check_button.setEnabled(False)
        self.update_button.setEnabled(False)
        QThreadPool.globalInstance().start(task)

    def refresh_versions(self):
        self.run_task(lambda: (self.runtime.version(), FFmpegService(self.runtime.ffmpeg_dir()).get_version()),
            lambda result: (self.engine_version.setText(result[0]), self.ffmpeg_version.setText(result[1])))

    def check_updates(self):
        self.update_status.setText("Checking the official release…")
        self.run_task(lambda: (self.runtime.version(), self.runtime.check_update()),
            lambda versions: self.update_status.setText("You are up to date." if versions[0] == versions[1] else f"Available: {versions[1]} · Installed: {versions[0]}"))

    def update_engine(self):
        if self.service.active or self.service.inspectors:
            self.update_status.setText("Pause active downloads and wait for link inspection to finish before updating.")
            return
        self.update_status.setText("Downloading and verifying the new engine…")
        self.service.maintenance = True
        task = Task(self.runtime.update)
        def success(version):
            self.config.set("yt_dlp_path", "")
            self.engine_version.setText(version)
            self.update_status.setText(f"Updated to {version}. Your downloads and settings are preserved.")
        def finished():
            self.service.maintenance = False
            self.check_button.setEnabled(True)
            self.update_button.setEnabled(True)
            self.service._pump()
            self.service.activity.emit()
        task.signals.result.connect(success)
        task.signals.error.connect(lambda _: self.update_status.setText("Update failed. The installed engine was kept. Check your connection and try again."))
        task.signals.finished.connect(finished)
        self.check_button.setEnabled(False)
        self.update_button.setEnabled(False)
        QThreadPool.globalInstance().start(task)

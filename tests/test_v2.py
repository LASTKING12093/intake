"""V2 contract tests: adapters, matching, preservation and native interaction states."""
import json
import sqlite3
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QThreadPool
from app.utils.urls import parse_urls,source_name
from app.services import catalog
from app.services.catalog import match_score,CatalogError,spotify_entity,apple_track
from app.models.download import Options,State
from app.services.formats import format_selector,postprocess_args
from app.utils.paths import migrate_legacy
from app.ui.motion import Motion
from app.ui.main_window import MainWindow

TRACK={'title':'First Light','artist':'Intake Studio','duration':180,'catalog':'Spotify'}

@pytest.mark.parametrize('url,source',[('https://www.tiktok.com/@studio/video/123','TikTok'),('https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT','Spotify'),('https://music.apple.com/us/album/name/123?i=456','Apple Music'),('https://vimeo.com/123456','Compatible source'),('https://youtube.com.evil.org/watch?v=abcdefghijk','Compatible source'),('https://youtube.com/@Blender/videos','YouTube')])
def test_universal_sources(url,source):
    parsed=parse_urls(url); assert len(parsed)==1; assert source_name(parsed[0])==source


def test_smart_quality_and_explicit_codec_constraints():
    assert format_selector(Options(container='Auto'))=='bv+ba/b'
    assert 'avc' not in format_selector(Options(container='Auto'))
    assert 'vcodec^=av01' in format_selector(Options(container='Auto',video_codec='AV1'))
    assert format_selector(Options(mode='Audio',audio_codec='Opus'))=='bestaudio[acodec^=opus]/best[acodec^=opus]'
    args=postprocess_args(Options(container='Auto')); assert args[args.index('--merge-output-format')+1]=='mkv'


def test_spotify_public_album_and_no_preview_download():
    entity={'id':'album','type':'album','title':'Quiet Hours','subtitle':'Intake Studio','trackList':[{'uri':'spotify:track:4cOdK2wGLETKBW3PvgPWqT','title':'First Light','subtitle':'Intake Studio','duration':180000,'audioPreview':{'url':'https://example.com/preview.mp3'}}]}
    info=spotify_entity(entity,'https://open.spotify.com/album/example')
    assert info['entries'][0]['duration']==180
    assert info['entries'][0]['album']=='Quiet Hours'
    assert info['entries'][0]['needs_catalog']
    assert 'preview' not in json.dumps(info)


def test_spotify_track_metadata():
    info=spotify_entity({'id':'x','type':'track','title':'First Light','duration':180000,'artists':[{'name':'Intake Studio'}],'visualIdentity':{'image':[{'url':'small','maxHeight':64},{'url':'large','maxHeight':640}]}},'url')
    assert info['artist']=='Intake Studio' and info['thumbnail']=='large'
    with pytest.raises(CatalogError): spotify_entity({'type':'playlist','title':'Private'},'url')


def test_apple_track_and_playlist(monkeypatch):
    song={'kind':'song','trackId':123,'trackName':'First Light','artistName':'Intake Studio','trackTimeMillis':180000,'collectionName':'Quiet Hours','artworkUrl100':'https://example.com/100x100bb.jpg'}
    assert apple_track(song)['thumbnail'].endswith('600x600bb.jpg')
    page='<title>Quiet Hours - Playlist - Apple Music</title><script id="serialized-server-data">'+json.dumps({'items':[{'kind':'song','identifiers':{'storeAdamID':'123'}},{'kind':'song','identifiers':{'storeAdamID':'123'}}]})+'</script>'
    monkeypatch.setattr(catalog,'request',lambda url,*args:page.encode() if 'music.apple.com' in url else json.dumps({'results':[song]}).encode())
    info=catalog.apple('https://music.apple.com/us/playlist/quiet/pl.example')
    assert len(info['entries'])==1 and info['entries'][0]['playlist_index']==1


def test_matching_rejects_wrong_recording():
    exact={'title':'Intake Studio — First Light (Official Audio)','channel':'Intake Studio','duration':181}
    assert match_score(TRACK,exact)>.95
    assert match_score(TRACK,dict(exact,title='First Light cover by Someone'))<.78
    assert match_score(TRACK,dict(exact,duration=45))==0
    assert match_score(TRACK,dict(exact,title='First Light (Live)'))<.78
    assert match_score(TRACK,dict(exact,title='Intake Studio First Light (2022 Remaster)'))<.78


def test_uncertain_match_cannot_bypass_review_via_queue(service,monkeypatch):
    job=service.add('https://open.spotify.com/track/example',dict(TRACK,source_url='https://example.com/media',match_score=.5),Options(mode='Audio'))
    started=[]; monkeypatch.setattr(service,'_pump',lambda:started.append(True))
    service.enqueue(job); assert job.state==State.FAILED and not started
    job.info['match_approved']=True; service.enqueue(job); assert job.state==State.WAITING and started


def test_lyrics_optional(monkeypatch):
    monkeypatch.setattr(catalog,'request',lambda *args:json.dumps({'syncedLyrics':'[00:01.00]Original fixture lyric'}).encode())
    assert catalog.lyrics_for(TRACK)['extension']=='.lrc'
    monkeypatch.setattr(catalog,'request',lambda *args:(_ for _ in ()).throw(OSError()))
    assert catalog.lyrics_for(TRACK) is None


def test_legacy_migration_never_overwrites_or_moves(tmp_path):
    legacy=tmp_path/'MediaGrab'; legacy.mkdir(); target=tmp_path/'INTAKE'
    (legacy/'config.json').write_text('{"download_folder":"custom"}'); (legacy/'queue.json').write_text('[]')
    with sqlite3.connect(legacy/'history.sqlite3') as db: db.execute('CREATE TABLE saved(title TEXT)'); db.execute("INSERT INTO saved VALUES ('kept')")
    migrate_legacy(target,legacy); assert (legacy/'config.json').exists()
    with sqlite3.connect(target/'history.sqlite3') as db: assert db.execute('SELECT title FROM saved').fetchone()==('kept',)
    (target/'config.json').write_text('new'); migrate_legacy(target,legacy); assert (target/'config.json').read_text()=='new'


def settle(qtbot,window):
    QThreadPool.globalInstance().waitForDone(30000); qtbot.wait(100); window.close()


def test_home_states_keyboard_mandatory_motion_and_sizes(qtbot,config,monkeypatch):
    config.set('motion','Reduced'); window=MainWindow(config); qtbot.addWidget(window); window.show(); qtbot.wait(450)
    out=Path('.test-data/screenshots/v2'); out.mkdir(parents=True,exist_ok=True)
    assert 'motion' not in __import__('app.services.config',fromlist=['DEFAULTS']).DEFAULTS; assert not window.result_host.isVisible(); assert not window.queue_hint.isVisible()
    assert window.composer.source.manual=='Auto Detect'; assert len(window.nav)==4
    for width,height in [(860,620),(1160,800),(1600,1000)]:
        window.resize(width,height); qtbot.wait(30); window.grab().save(str(out/f'empty-{width}.png'))
        assert window.home_scroll.horizontalScrollBar().maximum()==0
    window.resize(1160,800); qtbot.wait(30)
    # Repeated renders must retain header artwork and navigation, including clips.
    first=window.grab().toImage().copy(0,0,1160,100)
    second=window.grab().toImage().copy(0,0,1160,100)
    assert first==second
    assert any(first.pixelColor(x,50).value()>200 for x in range(76,146))
    pending=[]; monkeypatch.setattr(window.service,'get_info',lambda url:pending.append(url))
    window.url.setPlainText('https://youtu.be/abcdefghijk'); qtbot.keyClick(window.url,Qt.Key.Key_Return)
    assert pending and window.composer.busy.isVisible(); window.grab().save(str(out/'analyzing.png'))
    info={'title':'A quiet afternoon','channel':'INTAKE Studio','duration':153,'formats':[{'height':2160,'vcodec':'av01','ext':'webm'},{'height':1080,'vcodec':'avc1','ext':'mp4'}],'subtitles':{'en':[]}}
    window.service.info_ready.emit(pending[0],info); qtbot.wait(450); card=window.current_result
    assert card.job.options.container=='Auto' and not card.advanced.isVisible()
    assert not window.composer.busy.isVisible(); assert window.composer.source.text().startswith('YouTube')
    card.toggle_options(); assert card.advanced.isVisible(); assert card.quality.findText('2160p')>=0
    window.resize(860,620); qtbot.wait(30); assert window.home_scroll.horizontalScrollBar().maximum()==0; window.grab().save(str(out/'options-min.png'))
    card.toggle_options(); window.resize(1160,800); qtbot.wait(450); window.grab().save(str(out/'detected.png'))
    # No downloads or fake backend calls: render a controlled model state.
    job=card.job; job.state=State.DOWNLOADING; job.progress=68; job.total=20*1024*1024; job.speed=2*1024*1024
    window.refresh_card(job); qtbot.wait(400); assert window.current_result is card; assert card.bar.value()==680; window.grab().save(str(out/'progress.png'))
    job.state=State.COMPLETED; job.output=str(out/'original.mp4'); window.refresh_card(job); assert 'Yours offline' in card.status.text(); assert not card.bar.isVisible(); window.grab().save(str(out/'complete.png'))
    window.show_page(1); qtbot.wait(450); window.grab().save(str(out/'queue.png'))
    window.history.record(job); window.show_page(2); qtbot.wait(450); window.grab().save(str(out/'library.png'))
    window.history_page.search.setText('missing'); assert not window.history_page.filtered_rows()
    window.history_page.search.clear(); assert len(window.history_page.filtered_rows())==1
    window.show_page(3); qtbot.wait(450); window.grab().save(str(out/'settings.png'))
    qtbot.keyClick(window,Qt.Key.Key_L,Qt.KeyboardModifier.ControlModifier); assert window.pages.currentIndex()==0 and window.url.hasFocus()
    settle(qtbot,window)


def test_source_override_duplicate_and_error(qtbot,config,monkeypatch):
    window=MainWindow(config); qtbot.addWidget(window); window.show(); calls=[]
    monkeypatch.setattr(window.service,'get_info',lambda url:calls.append(url))
    window.composer.source.select('Spotify'); window.url.setPlainText('https://youtu.be/abcdefghijk'); window.add_links(); assert not calls and 'Auto Detect' in window.message.text()
    window.composer.source.select('Auto Detect'); window.add_links(); window.service.info_ready.emit(calls[0],{'title':'Film'}); window.add_links(); assert len(window.cards)==1
    window.info_failed('url','Network problem. Try again.'); assert window.error_actions.isVisible()
    settle(qtbot,window)

def test_full_motion_navigation_and_interruptible_options(qtbot,config,monkeypatch):
    config.set('motion','Reduced'); window=MainWindow(config); qtbot.addWidget(window); window.show(); qtbot.wait(300)
    start=window.navigation.indicator.pos(); window.show_page(2)
    animation=window.navigation.indicator._motion_pos
    assert animation.duration()==420
    page=window.pages.currentWidget()
    assert page._motion_pos.duration()==380 and page.x()>0
    qtbot.wait(70); middle=window.navigation.indicator.pos()
    assert start.x()<middle.x()<window.navigation.indicator_position(2).x()
    assert 0<page.x()<48
    qtbot.wait(400); assert window.navigation.indicator.pos()==window.navigation.indicator_position(2)
    window.show_page(3); qtbot.wait(50); window.show_page(1); qtbot.wait(50); window.show_page(0)
    qtbot.wait(450); assert window.pages.currentWidget().pos().isNull()
    job=window.service.add('https://youtu.be/abcdefghijk',{'title':'Motion fixture'},Options(container='Auto'))
    qtbot.wait(450); card=window.current_result; card.toggle_options(); qtbot.wait(70); card.toggle_options(); qtbot.wait(450)
    assert not card.advanced.isVisible()
    window.service.remove(job); qtbot.wait(450); assert not window.cards and not window.result_host.isVisible()
    settle(qtbot,window)


@pytest.mark.parametrize('platform',['youtube','tiktok','spotify','applemusic'])
def test_platform_assets_preserve_color(qapp,platform):
    from app.ui.assets import icon
    image=icon(platform,'#ffffff',32).pixmap(32,32).toImage()
    pixels=[image.pixelColor(x,y) for x in range(image.width()) for y in range(image.height())]
    colorful=[c for c in pixels if c.alpha()>200 and max(c.red(),c.green(),c.blue())-min(c.red(),c.green(),c.blue())>80]
    assert len(colorful)>20
    if platform=='tiktok':
        assert any(c.red()>200 and c.green()<100 for c in colorful)
        assert any(c.green()>190 and c.blue()>190 and c.red()<100 for c in colorful)
    if platform=='youtube':
        assert any(c.red()>230 and c.green()<50 for c in colorful)
        assert any(c.alpha()>200 and min(c.red(),c.green(),c.blue())>240 for c in pixels)


def test_legacy_motion_settings_cannot_disable_animation(qapp,tmp_path,monkeypatch):
    import ctypes
    from app.services.config import Config
    from PySide6.QtWidgets import QWidget
    from PySide6.QtCore import QPoint
    # Fail if any code consults the Windows animation preference.
    def no_os_preference(*args):
        raise AssertionError('Motion must be independent of the Windows preference')
    monkeypatch.setattr(ctypes.windll.user32,'SystemParametersInfoW',no_os_preference)
    path=tmp_path/'legacy.json'; path.write_text(json.dumps({'motion':'Reduced'}),encoding='utf-8')
    config=Config(path); assert 'motion' not in config.values
    target=QWidget(); target.move(0,0)
    animation=Motion.animate(target,b'pos',QPoint(30,0))
    assert animation.duration()==320
    animation.stop(); target.close()

"""Public catalog metadata adapters. Never fetch DRM media, previews or session tokens."""
import html
import json
import re
import unicodedata
import urllib.request
from urllib.parse import urlparse, parse_qs, urlencode
from app.utils.urls import source_name
from app.services.process import Interrupted

class CatalogError(RuntimeError):
    pass


def request(url, limit=5*1024*1024, timeout=20):
    parsed=urlparse(url)
    if parsed.scheme not in {'https','http'} or parsed.username or parsed.password:
        raise CatalogError('This metadata address is not a supported web URL.')
    req=urllib.request.Request(url,headers={'User-Agent':'INTAKE/2.0 (desktop media metadata)','Accept':'application/json,text/html'})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        data=response.read(limit+1)
    if len(data)>limit: raise CatalogError('This catalog response is too large. Try an individual track link.')
    return data


def script_json(page, identifier):
    match=re.search(r'<script\b[^>]*'+identifier+r'[^>]*>(.*?)</script>',page,re.S)
    if not match: raise CatalogError('This catalog is not publicly readable. Try a public track or album link.')
    return json.loads(html.unescape(match[1]))


def spotify_entity(entity,url):
    images=entity.get('visualIdentity',{}).get('image',[])
    image=max(images,key=lambda x:x.get('maxHeight',0),default={}).get('url','')
    artist=', '.join(a.get('name','') for a in entity.get('artists',[])) or entity.get('subtitle','')
    base={'id':entity.get('id',''), 'title':entity.get('title') or entity.get('name',''), 'artist':artist,
          'channel':artist, 'duration':(entity.get('duration') or 0)/1000, 'thumbnail':image,
          'catalog':'Spotify','webpage_url':url,'release_date':(entity.get('releaseDate') or {}).get('isoString','')[:10]}
    if entity.get('type') in ('playlist','album'):
        entries=[]
        for i,track in enumerate(entity.get('trackList',[]),1):
            uri=track.get('uri','').split(':')
            if len(uri)!=3 or uri[1]!='track': continue
            entries.append(dict(id=uri[-1],title=track.get('title',''),artist=track.get('subtitle',''),channel=track.get('subtitle',''),
                duration=(track.get('duration') or 0)/1000,thumbnail=image,catalog='Spotify',
                webpage_url='https://open.spotify.com/track/'+uri[-1],playlist_index=i,playlist_title=base['title'],
                album=base['title'] if entity['type']=='album' else '',needs_catalog=True))
        if not entries: raise CatalogError('Spotify did not expose tracks for this collection. Try a public track or album link.')
        base.update(entries=entries,collection_notice='Tracks exposed by the public Spotify embed. Restricted or undisclosed tracks cannot be included.')
    elif not base['title'] or not artist:
        raise CatalogError('Spotify did not return enough metadata to identify this track.')
    return base


def spotify(url):
    match=re.search(r'/(?:intl-[^/]+/)?(track|album|playlist)/([A-Za-z0-9]{22})',urlparse(url).path)
    if not match: raise CatalogError('Use a full Spotify track, album or playlist link from open.spotify.com.')
    page=request('https://open.spotify.com/embed/'+match[1]+'/'+match[2]).decode('utf-8')
    data=script_json(page,r'id="__NEXT_DATA__"')
    try: entity=data['props']['pageProps']['state']['data']['entity']
    except KeyError: raise CatalogError('Spotify is not sharing this collection publicly. Try an individual public track or album.')
    return spotify_entity(entity,url)


def apple_track(track):
    return dict(id=str(track['trackId']),title=track.get('trackName',''),artist=track.get('artistName',''),channel=track.get('artistName',''),
        album=track.get('collectionName',''),duration=(track.get('trackTimeMillis') or 0)/1000,
        thumbnail=track.get('artworkUrl100','').replace('100x100bb','600x600bb'),catalog='Apple Music',
        webpage_url=track.get('trackViewUrl',''),playlist_index=track.get('trackNumber',0),
        release_date=track.get('releaseDate','')[:10],genre=track.get('primaryGenreName',''))


def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value,list):
        for child in value: yield from walk(child)


def apple(url):
    parsed=urlparse(url); parts=parsed.path.strip('/').split('/'); country=parts[0] if len(parts[0])==2 else 'us'
    track_id=parse_qs(parsed.query).get('i',[None])[0]
    if '/playlist/' in parsed.path:
        page=request(url).decode('utf-8'); data=script_json(page,r'id="serialized-server-data"')
        ids=[]
        for node in walk(data):
            ident=node.get('identifiers',{}).get('storeAdamID')
            if node.get('kind')=='song' and ident and str(ident) not in ids: ids.append(str(ident))
        title_match=re.search(r'<title>(.*?)</title>',page,re.S)
        title=html.unescape(title_match[1]).split(' - Playlist')[0] if title_match else 'Apple Music playlist'
        entries=[]
        for offset in range(0,len(ids),100):
            response=json.loads(request('https://itunes.apple.com/lookup?'+urlencode({'id':','.join(ids[offset:offset+100]),'country':country})))
            lookup={str(t['trackId']):apple_track(t) for t in response.get('results',[]) if t.get('kind')=='song'}
            entries.extend(lookup[i] for i in ids[offset:offset+100] if i in lookup)
        if not entries: raise CatalogError('Apple Music did not expose public tracks for this playlist. Try a track or album link.')
        for i,e in enumerate(entries,1): e.update(playlist_title=title,playlist_index=i)
        return dict(title=title,catalog='Apple Music',webpage_url=url,entries=entries,
                    collection_notice='Publicly listed tracks available in this storefront. Private or undisclosed tracks are not included.')
    ident=track_id or parts[-1]
    if not ident.isdigit(): raise CatalogError('Use an Apple Music track, album or public playlist link.')
    params={'id':ident,'country':country,'entity':'song','limit':200}
    response=json.loads(request('https://itunes.apple.com/lookup?'+urlencode(params)))
    entries=[apple_track(t) for t in response.get('results',[]) if t.get('kind')=='song']
    if not entries: raise CatalogError('This Apple Music release is unavailable in the selected storefront.')
    if track_id or '/song/' in parsed.path: return next((e for e in entries if e['id']==ident),entries[0])
    album=next((t for t in response['results'] if t.get('wrapperType')=='collection'),{})
    for e in entries: e['playlist_title']=album.get('collectionName','Album')
    return dict(title=album.get('collectionName',entries[0].get('album','Album')),catalog='Apple Music',webpage_url=url,
                thumbnail=entries[0]['thumbnail'],entries=entries,collection_notice='Catalog tracks available in this storefront (up to 200 per album).')


def catalog_info(url):
    return spotify(url) if source_name(url)=='Spotify' else apple(url)


def normalized(text):
    text=unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()
    return set(re.findall(r'[a-z0-9]+',text))


def match_score(track,candidate):
    title=normalized(track.get('title','')); artist=normalized(track.get('artist',''))
    candidate_title=normalized(candidate.get('title','')); channel=normalized(candidate.get('channel') or candidate.get('uploader',''))
    if not title or not artist: return 0.0
    score=.55*len(title&candidate_title)/len(title)+.3*len(artist&(candidate_title|channel))/len(artist)
    duration=track.get('duration') or 0; found=candidate.get('duration') or 0
    if duration and found:
        delta=abs(duration-found)
        if delta>max(20,duration*.12): return 0.0
        score+=.15*max(0,1-delta/20)
    # Do not silently replace an original with a cover, live performance or altered recording.
    variants={'live','cover','remix','remaster','remastered','karaoke','slowed','sped','instrumental'}
    if (candidate_title-title)&variants: score-=.35
    return round(max(0,score),3)


def inspect_media(runtime,runner,url,flat=True):
    result=[]
    args=runtime.base_args()+['--dump-single-json','--skip-download','--ignore-errors']
    if flat: args+=['--flat-playlist']
    runner.run(args+['--',url],lambda line:result.append(json.loads(line)) if line.startswith('{') else None)
    if not result or not result[0]: raise RuntimeError('Media unavailable')
    return result[0]


def match_music(runtime,runner,track):
    if runner.stop_event.is_set(): raise Interrupted()
    query=f"{track.get('artist','')} {track['title']} audio"
    result=inspect_media(runtime,runner,'ytsearch5:'+query)
    candidates=[]
    for entry in result.get('entries',[]):
        if not entry: continue
        url=entry.get('webpage_url') or entry.get('url','')
        if not url.startswith('https://'): continue
        candidates.append(dict(title=entry.get('title',''),channel=entry.get('channel') or entry.get('uploader',''),
                               duration=entry.get('duration') or 0,url=url,score=match_score(track,entry)))
    candidates.sort(key=lambda c:c['score'],reverse=True)
    if not candidates: raise CatalogError('No compatible audio source was found. Try a direct media link.')
    return dict(track,match_candidates=candidates,source_url=candidates[0]['url'],match_score=candidates[0]['score'],
                matched_title=candidates[0]['title'],matched_channel=candidates[0]['channel'])


def lyrics_for(info):
    if not info.get('artist') or not info.get('duration'): return None
    params={'track_name':info['title'],'artist_name':info['artist'],'duration':round(info['duration'])}
    if info.get('album'): params['album_name']=info['album']
    try:
        result=json.loads(request('https://lrclib.net/api/get?'+urlencode(params),512*1024,5))
        return {'text':result.get('syncedLyrics') or result.get('plainLyrics') or '',
                'extension':'.lrc' if result.get('syncedLyrics') else '.txt'}
    except Exception:
        return None  # Optional enrichment must not fail a media download.

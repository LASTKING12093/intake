import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def source_name(url):
    host=(urlparse(url).hostname or '').lower()
    if host == 'youtu.be' or host == 'youtube.com' or host.endswith('.youtube.com'): return 'YouTube'
    if host == 'tiktok.com' or host.endswith('.tiktok.com'): return 'TikTok'
    if host in {'open.spotify.com','spotify.link'}: return 'Spotify'
    if host in {'music.apple.com','itunes.apple.com'}: return 'Apple Music'
    return 'Compatible source'


def parse_urls(text):
    """Accept HTTP(S), no credentials or executable schemes; canonicalize YouTube."""
    result=[]
    for candidate in re.findall(r'(?:https?://|www\.|youtu\.be/|open\.spotify\.com/|music\.apple\.com/)[^\s<>"\']+',text,re.I):
        candidate=candidate.rstrip('.,;)]}')
        if not candidate.lower().startswith(('http://','https://')): candidate='https://'+candidate
        try:
            parsed=urlparse(candidate)
            if parsed.username or parsed.password or not parsed.hostname or parsed.port == 0: continue
        except ValueError: continue
        host=(parsed.hostname or '').lower(); query=parse_qs(parsed.query)
        if source_name(candidate)=='YouTube':
            video=None; playlist=query.get('list',[None])[0]
            if host=='youtu.be': video=parsed.path.strip('/').split('/')[0]
            elif parsed.path=='/watch': video=query.get('v',[None])[0]
            elif parsed.path.startswith(('/shorts/','/live/','/embed/')): video=parsed.path.split('/')[2]
            elif parsed.path.startswith(('/@','/channel/','/c/','/user/')):
                url='https://www.youtube.com'+parsed.path
                if url not in result: result.append(url)
                continue
            elif parsed.path!='/playlist': continue
            if video and not re.fullmatch(r'[\w-]{11}',video,re.ASCII): video=None
            if playlist and not re.fullmatch(r'[\w-]{10,100}',playlist,re.ASCII): playlist=None
            params={}
            if video: params['v']=video
            if playlist: params['list']=playlist
            if not params: continue
            candidate='https://www.youtube.com/'+('watch' if video else 'playlist')+'?'+urlencode(params)
        else:
            candidate=urlunparse(parsed._replace(fragment=''))
        if candidate not in result: result.append(candidate)
    return result

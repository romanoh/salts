"""
    SALTS XBMC Addon
    Copyright (C) 2014 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import scraper
import re
import urlparse
import xbmcaddon
import urllib
from salts_lib.db_utils import DB_Connection
from salts_lib.constants import VIDEO_TYPES
from salts_lib.constants import QUALITIES

BASE_URL = 'http://moviestorm.eu'
QUALITY_MAP = {'HD': QUALITIES.HIGH, 'CAM': QUALITIES.LOW, 'BRRIP': QUALITIES.HIGH, 'UNKNOWN': QUALITIES.MEDIUM, 'DVDRIP': QUALITIES.HIGH}

class MovieStorm_Scraper(scraper.Scraper):
    base_url = BASE_URL

    def __init__(self, timeout=scraper.DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.db_connection = DB_Connection()
        self.base_url = xbmcaddon.Addon().getSetting('%s-base_url' % (self.get_name()))

    @classmethod
    def provides(cls):
        return frozenset([VIDEO_TYPES.TVSHOW, VIDEO_TYPES.SEASON, VIDEO_TYPES.EPISODE, VIDEO_TYPES.MOVIE])

    @classmethod
    def get_name(cls):
        return 'moviestorm.eu'

    def resolve_link(self, link):
        if self.base_url in link:
            url = urlparse.urljoin(self.base_url, link)
            html = self._http_get(url, cache_limit=.5)
            match = re.search('class="real_link"\s+href="([^"]+)', html)
            if match:
                return match.group(1)
        else:
            return link

    def format_source_label(self, item):
        label = '[%s] %s (%s views)' % (item['quality'], item['host'], item['views'])
        return label

    def get_sources(self, video):
        source_url = self.get_url(video)
        hosters = []
        if source_url:
            url = urlparse.urljoin(self.base_url, source_url)
            html = self._http_get(url, cache_limit=.5)
            pattern = 'class="source_td">\s*<img[^>]+>\s*(.*?)\s*-\s*\((\d+) views\).*?class="quality_td">\s*(.*?)\s*<.*?href="([^"]+)'
            for match in re.finditer(pattern, html, re.DOTALL):
                host, views, quality_str, stream_url = match.groups()

                hoster = {'multi-part': False, 'host': host.lower(), 'class': self, 'url': stream_url, 'quality': self._get_quality(video, host, QUALITY_MAP.get(quality_str.upper())), 'views': views, 'rating': None, 'direct': False}
                hosters.append(hoster)
        return hosters

    def get_url(self, video):
        return super(MovieStorm_Scraper, self)._default_get_url(video)

    def _get_episode_url(self, show_url, video):
        episode_pattern = 'class="number left".*?href="([^"]+season-%d/episode-%d[^"]+)' % (int(video.season), int(video.episode))
        title_pattern = 'class="name left".*?href="([^"]+)">([^<]+)'
        airdate_pattern = 'class="edate[^>]+>\s*{p_month}-{p_day}-{year}.*?href="([^"]+)'
        return super(MovieStorm_Scraper, self)._default_get_episode_url(show_url, video, episode_pattern, title_pattern, airdate_pattern)

    def search(self, video_type, title, year):
        url = urlparse.urljoin(self.base_url, '/search?q=%s&go=Search' % urllib.quote_plus(title))
        html = self._http_get(url, cache_limit=8)

        results = []
        pattern = 'class="movie_box.*?href="([^"]+).*?<h1>([^<]+)'
        norm_title = self._normalize_title(title)
        for match in re.finditer(pattern, html, re.DOTALL):
            url, match_title = match.groups()
            if norm_title in self._normalize_title(match_title):
                result = {'url': url.replace(self.base_url, ''), 'title': match_title, 'year': ''}
                results.append(result)

        return results

    def _http_get(self, url, data=None, cache_limit=8):
        return super(MovieStorm_Scraper, self)._cached_http_get(url, self.base_url, self.timeout, data=data, cache_limit=cache_limit)

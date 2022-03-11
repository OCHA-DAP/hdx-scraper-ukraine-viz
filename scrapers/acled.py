import logging
from itertools import chain

from hdx.scraper.base_scraper import BaseScraper
from hdx.utilities.dateparse import default_date, parse_date

logger = logging.getLogger(__name__)

hxltags = {
    "event_date": "#date+occurred",
    "event_type": "#event+type",
    "sub_event_type": "#event+type+sub",
    "actor1": "#group+name+first",
    "actor2": "#group+name+second",
    "admin1": "#adm1+name",
    "admin2": "#adm2+name",
    "admin3": "#adm3+name",
    "location": "#loc+name",
    "latitude": "#geo+lat",
    "longitude": "#geo+lon",
    "notes": "#description",
    "fatalities": "#affected+killed",
}


class ACLED(BaseScraper):
    def __init__(self, datasetinfo, today, outputs, downloader, other_auths):
        super().__init__("acled", datasetinfo, dict())
        self.today = today
        self.outputs = outputs
        self.downloader = downloader
        self.auth = other_auths[self.name]

    def run(self):
        start_date = parse_date(self.datasetinfo["start_date"])
        years = range(start_date.year, self.today.year + 1)
        iterables = list()
        for year in years:
            url = f"{self.datasetinfo['url'] % year}&{self.auth}"
            headers, iterator = self.downloader.get_tabular_rows(
                url,
                dict_form=True,
            )
            iterables.append(iterator)
        latest_date = default_date
        rows = [list(hxltags.keys()), list(hxltags.values())]
        for inrow in chain.from_iterable(iterables):
            date = parse_date(inrow["event_date"])
            if date < start_date:
                continue
            if date > latest_date:
                latest_date = date
            row = list()
            for header in hxltags:
                row.append(inrow[header])
            rows.append(row)
        tabname = "fatalities"
        for output in self.outputs.values():
            output.update_tab(tabname, rows)
        self.datasetinfo["date"] = latest_date

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
    "adm1_pcode": "#adm1+code",
    "location": "#loc+name",
    "latitude": "#geo+lat",
    "longitude": "#geo+lon",
    "notes": "#description",
    "fatalities": "#affected+killed",
}


class ACLED(BaseScraper):
    def __init__(
        self,
        datasetinfo,
        start_date,
        today,
        outputs,
        adminone,
    ):
        # ACLED outputs to its own tab "fatalities" so there are no headers
        super().__init__("acled", datasetinfo, dict())
        self.start_date = start_date
        self.today = today
        self.outputs = outputs
        self.adminone = adminone

    def run(self):
        years = range(self.start_date.year, self.today.year + 1)
        iterables = list()
        retriever = self.get_retriever()
        for year in years:
            url = self.datasetinfo["url"] % year
            headers, iterator = retriever.get_tabular_rows(url, dict_form=True)
            iterables.append(iterator)
        latest_date = default_date
        rows = [list(hxltags.keys()), list(hxltags.values())]
        for inrow in chain.from_iterable(iterables):
            date = parse_date(inrow["event_date"])
            if date < self.start_date:
                continue
            event_type = inrow["event_type"].lower()
            if event_type in ("protests", "strategic developments"):
                continue
            if (
                event_type == "riots"
                and inrow["sub_event_type"].lower() == "violent demonstration"
            ):
                continue
            if date > latest_date:
                latest_date = date
            adm1name = inrow["admin1"]
            pcode = None
            if adm1name:
                pcode, _ = self.adminone.get_pcode("UKR", adm1name)
            inrow["adm1_pcode"] = pcode
            row = list()
            for header in hxltags:
                row.append(inrow[header])
            rows.append(row)
        tabname = "fatalities"
        for output in self.outputs.values():
            output.update_tab(tabname, rows)
        self.datasetinfo["source_date"] = latest_date

    def add_sources(self):
        self.add_hxltag_source("fatalities", "#date+latest+acled")

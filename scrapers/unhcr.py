import logging
from hdx.location.country import Country
from hdx.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class UNHCR(BaseScraper):
    def __init__(self, datasetinfo, today, outputs, downloader):
        super().__init__(
            "unhcr",
            datasetinfo,
            {
                "national": (
                    ("NoRefugees", "RefugeesDate"),
                    ("#affected+refugees", "#affected+date+refugees"),
                )
            },
        )
        self.today = today
        self.outputs = outputs
        self.downloader = downloader

    def run(self):
        url = self.datasetinfo["url"]
        valuedicts = self.get_values("national")
        r = self.downloader.download(url)
        for data in r.json()["data"]:
            individuals = data["individuals"]
            date = data["date"]
            countryiso3, _ = Country.get_iso3_country_code_fuzzy(data["geomaster_name"])
            valuedicts[0][countryiso3] = int(individuals)
            valuedicts[1][countryiso3] = date

        url = self.datasetinfo["url_series"]
        r = self.downloader.download(url)
        rows = [("RefugeesDate", "NoRefugees"), ("#affected+date+refugees", "#affected+refugees")]
        for data in r.json()["data"]["timeseries"]:
            rows.append((data["data_date"], data["individuals"]))
        tabname = "refugees_series"
        for output in self.outputs.values():
            output.update_tab(tabname, rows)
        self.datasetinfo["date"] = self.today


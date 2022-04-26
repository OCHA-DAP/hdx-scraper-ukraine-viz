import logging

from hdx.location.country import Country
from hdx.scraper.base_scraper import BaseScraper
from hdx.utilities.retriever import Retrieve

logger = logging.getLogger(__name__)


class UNHCR(BaseScraper):
    def __init__(self, datasetinfo, today, outputs, countryiso3s):
        super().__init__(
            "unhcr",
            datasetinfo,
            {
                "national": (
                    ("NoRefugees", "RefugeesDate"),
                    ("#affected+refugees", "#affected+date+refugees"),
                ),
                "regional": (
                    ("NoRefugees",),
                    ("#affected+refugees",),
                ),
            },
        )
        self.today = today
        self.outputs = outputs
        self.countryiso3s = countryiso3s

    def run(self):
        url = self.datasetinfo["url"]
        valuedicts = self.get_values("national")
        retriever = self.get_retriever()
        json = retriever.download_json(url)
        total_refugees = 0
        for data in json["data"]:
            individuals = int(data["individuals"])
            total_refugees += individuals
            date = data["date"]
            countryiso3, _ = Country.get_iso3_country_code_fuzzy(data["geomaster_name"])
            if countryiso3 in self.countryiso3s:
                valuedicts[0][countryiso3] = individuals
                valuedicts[1][countryiso3] = date
        self.get_values("regional")[0]["value"] = total_refugees

        url = self.datasetinfo["url_series"]
        json = retriever.download_json(url)
        rows = [
            ("RefugeesDate", "NoRefugees"),
            ("#affected+date+refugees", "#affected+refugees"),
        ]
        for data in json["data"]["timeseries"]:
            rows.append((data["data_date"], data["individuals"]))
        tabname = "refugees_series"
        for output in self.outputs.values():
            output.update_tab(tabname, rows)
        self.datasetinfo["source_date"] = self.today

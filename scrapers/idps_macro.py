import logging

from hdx.data.dataset import Dataset
from hdx.location.country import Country
from hdx.scraper.base_scraper import BaseScraper
from hdx.scraper.utilities.readers import read

logger = logging.getLogger(__name__)


class IDPsMacro(BaseScraper):
    def __init__(self, datasetinfo, today, outputs, downloader):
        super().__init__("idps_macro", datasetinfo, dict())
        self.today = today
        self.outputs = outputs
        self.downloader = downloader

    def run(self):
        headers, iterator = read(self.downloader, self.datasetinfo, self.today)
        rows = [
            ("Macro region", "IDP estimation"),
            ("#region+macro+name", "#affected+idps"),
        ]
        for inrow in iterator:
            rows.append(
                (inrow["Macro-region"], inrow["# est. IDPs presence per macro-region"])
            )
        tabname = "idps_macro"
        for output in self.outputs.values():
            output.update_tab(tabname, rows)

    def add_sources(self):
        self.add_hxltag_source("idps_macro", "#affected+idps")

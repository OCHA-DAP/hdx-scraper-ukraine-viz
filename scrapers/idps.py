import logging

from hdx.scraper.base_scraper import BaseScraper
from hdx.scraper.utilities.readers import read

logger = logging.getLogger(__name__)


class IDPs(BaseScraper):
    def __init__(self, datasetinfo, today, outputs):
        super().__init__(
            "idps",
            datasetinfo,
            {
                "national": (
                    ("IDP estimation",),
                    ("#affected+idps",),
                ),
            },
        )
        self.today = today
        self.outputs = outputs

    def run(self):
        retriever = self.get_retriever()
        headers, iterator = read(retriever, self.datasetinfo, self.today)
        total = 0
        rows = [
            ("Macro region", "IDP estimation"),
            ("#region+macro+name", "#affected+idps"),
        ]
        for inrow in iterator:
            idps = int(inrow["# est. IDPs presence per macro-region"])
            total += idps
            rows.append((inrow["Macro-region"], idps))
        valuedict = self.get_values("national")[0]
        valuedict["UKR"] = total
        tabname = "idps_macro"
        for output in self.outputs.values():
            output.update_tab(tabname, rows)

import logging

from hdx.scraper.base_scraper import BaseScraper

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
        reader = self.get_reader()
        headers, iterator = reader.read(self.datasetinfo)
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

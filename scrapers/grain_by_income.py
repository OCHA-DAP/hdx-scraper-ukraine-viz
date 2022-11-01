import logging

from hdx.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GrainByIncome(BaseScraper):
    def __init__(self, datasetinfo, outputs):
        super().__init__(
            "grain_by_income",
            datasetinfo,
            {
                "national": (
                    ("TonnageWheatToLowerIncome", "PercentWheatToLowerIncome",),
                    ("#indicator+commodities+wheat+num", "#indicator+commodities+wheat+pct",),
                ),
            },
        )
        self.outputs = outputs

    def run(self):
        reader = self.get_reader()
        headers, iterator = reader.read(self.datasetinfo)
        tonnage_total = 0
        tonnage_lowincome = 0
        pct_lowincome = 0
        for inrow in iterator:
            if inrow["Commodity"] != "Wheat":
                continue
            tons = int(inrow["total metric tons"].replace(",", ""))
            tonnage_total += tons
            if inrow["Income group"] in ["low-income", "lower-middle income"]:
                tonnage_lowincome += tons
        if tonnage_total > 0:
            pct_lowincome = tonnage_lowincome / tonnage_total
        valuedict = self.get_values("national")
        valuedict[0]["UKR"] = tonnage_lowincome
        valuedict[1]["UKR"] = pct_lowincome

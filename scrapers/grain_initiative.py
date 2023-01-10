import logging

from hdx.scraper.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class GrainInitiative(BaseScraper):
    def __init__(self, datasetinfo, outputs):
        super().__init__(
            "grain_initiative",
            datasetinfo,
            {
                "national": (
                    (
                        "NumberOfVoyages",
                        "TonnageOfCommodities",
                        "TonnageWheatToLowerIncome",
                        "PercentWheatToLowerIncome",
                    ),
                    (
                        "#indicator+voyages+num",
                        "#indicator+commodities+num",
                        "#indicator+commodities+wheat+num",
                        "#indicator+commodities+wheat+pct",
                    ),
                ),
            },
        )
        self.outputs = outputs

    def run(self):
        reader = self.get_reader()
        headers, iterator = reader.read(self.datasetinfo)
        tonnage = 0
        voyages = 0
        latest_date = None
        wheat_total = 0
        wheat_lowincome = 0
        pct_wheat_lowincome = 0
        for inrow in iterator:
            date = inrow["Inspection İstanbul"]
            if date and (not latest_date or latest_date < date):
                latest_date = date
            tons = int(inrow["Tonnage"])
            tonnage += tons
            voyage = inrow["Outbound Sequence"]
            if voyage and int(voyage) > voyages:
                voyages = int(voyage)
            if inrow["Commodity"] != "Wheat":
                continue
            wheat_total += tons
            if inrow["Income group"] in ["low-income", "lower-middle income"]:
                wheat_lowincome += tons
        if wheat_total > 0:
            pct_wheat_lowincome = wheat_lowincome / wheat_total
        valuedict = self.get_values("national")
        valuedict[0]["UKR"] = voyages
        valuedict[1]["UKR"] = tonnage
        valuedict[2]["UKR"] = wheat_lowincome
        valuedict[3]["UKR"] = pct_wheat_lowincome
        self.datasetinfo["source_date"] = latest_date

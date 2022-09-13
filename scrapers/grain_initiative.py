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
                    ("NumberOfVoyages", "TonnageOfCommodities",),
                    ("#indicator+voyages+num", "#indicator+commodities+num",),
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
        for inrow in iterator:
            date = inrow["Inspection İstanbul"]
            if date and (not latest_date or latest_date < date):
                latest_date = date
            tons = int(inrow["Tonnage"])
            tonnage += tons
            voyage = inrow["Outbound Sequence"]
            if voyage and int(voyage) > voyages:
                voyages = int(voyage)
        valuedict = self.get_values("national")
        valuedict[0]["UKR"] = voyages
        valuedict[1]["UKR"] = tonnage
        self.datasetinfo["source_date"] = latest_date

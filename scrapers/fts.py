import logging

from dateutil.relativedelta import relativedelta
from hdx.scraper.base_scraper import BaseScraper
from hdx.utilities.dictandlist import dict_of_lists_add
from hdx.utilities.downloader import Download
from hdx.utilities.text import get_fraction_str

logger = logging.getLogger(__name__)


class FTSException(Exception):
    pass


class FTS(BaseScraper):
    def __init__(self, datasetinfo, today, countryiso3s, basic_auths):
        base_hxltags = [
            "#value+funding+hrp+required+usd",
            "#value+funding+hrp+total+usd",
            "#value+funding+hrp+pct",
        ]
        national_hxltags = base_hxltags + [
            "#value+funding+other+plan_name",
            "#value+funding+other+required+usd",
            "#value+funding+other+total+usd",
            "#value+funding+other+pct",
        ]

        super().__init__(
            "fts",
            datasetinfo,
            {
                "national": (
                    (
                        "RequiredHRPFunding",
                        "HRPFunding",
                        "HRPPercentFunded",
                        "OtherPlans",
                        "RequiredOtherPlansFunding",
                        "OtherPlansFunding",
                        "OtherPlansPercentFunded",
                    ),
                    tuple(national_hxltags),
                ),
                "regional": (
                    ("RequiredFunding", "Funding", "PercentFunded"),
                    tuple(base_hxltags),
                ),
            },
        )
        self.today = today
        self.countryiso3s = countryiso3s
        self.basic_auths = basic_auths

    def download(self, url, downloader):
        r = downloader.download(url)
        json = r.json()
        status = json["status"]
        if status != "ok":
            raise FTSException(f"{url} gives status {status}")
        return json

    def download_data(self, url, downloader):
        return self.download(url, downloader)["data"]

    def get_requirements_and_funding_location(
        self, base_url, plan, countryid_iso3mapping, downloader
    ):
        countryreqs, countryfunds = dict(), dict()
        plan_id = plan["id"]
        url = f"{base_url}1/fts/flow/custom-search?planid={plan_id}&groupby=location"
        data = self.download_data(url, downloader)
        requirements = data["requirements"]
        totalreq = requirements["totalRevisedReqs"]
        countryreq_is_totalreq = True
        for reqobj in requirements["objects"]:
            countryid = reqobj.get("id")
            if not countryid:
                continue
            countryiso = countryid_iso3mapping.get(str(countryid))
            if not countryiso:
                continue
            if countryiso not in self.countryiso3s:
                continue
            req = reqobj.get("revisedRequirements")
            if req:
                countryreqs[countryiso] = req
                if req != totalreq:
                    countryreq_is_totalreq = False
        if countryreq_is_totalreq:
            countryreqs = dict()
            logger.info(
                f"{plan_id} has same country requirements as total requirements!"
            )

        fundingobjects = data["report3"]["fundingTotals"]["objects"]
        if len(fundingobjects) != 0:
            objectsbreakdown = fundingobjects[0].get("objectsBreakdown")
            if objectsbreakdown:
                for fundobj in objectsbreakdown:
                    countryid = fundobj.get("id")
                    if not countryid:
                        continue
                    countryiso = countryid_iso3mapping.get(countryid)
                    if not countryiso:
                        continue
                    if countryiso not in self.countryiso3s:
                        continue
                    countryfunds[countryiso] = fundobj["totalFunding"]
        return countryreqs, countryfunds

    def run(self) -> None:
        (
            hrp_requirements,
            hrp_funding,
            hrp_percentage,
            other_planname,
            other_requirements,
            other_funding,
            other_percentage,
        ) = self.get_values("national")

        def add_other_requirements_and_funding(iso3, name, req, fund, pct):
            dict_of_lists_add(other_planname, iso3, name)
            if req:
                dict_of_lists_add(other_requirements, iso3, req)
                if fund:
                    dict_of_lists_add(other_percentage, iso3, pct)
                else:
                    dict_of_lists_add(other_percentage, iso3, None)
            else:
                dict_of_lists_add(other_requirements, iso3, None)
                dict_of_lists_add(other_percentage, iso3, None)
            if fund:
                dict_of_lists_add(other_funding, iso3, fund)
            else:
                dict_of_lists_add(other_funding, iso3, None)

        base_url = self.datasetinfo["url"]

        with Download(
            basic_auth=self.basic_auths.get("fts"), rate_limit={"calls": 1, "period": 1}
        ) as downloader:
            curdate = self.today - relativedelta(months=1)
            url = f"{base_url}2/fts/flow/plan/overview/progress/{curdate.year}"
            data = self.download_data(url, downloader)
            plans = data["plans"]
            regional_plans = dict()
            for plan in plans:
                plan_name = plan["name"]
                allreq = plan["requirements"]["revisedRequirements"]
                funding = plan.get("funding")
                if funding:
                    allfund = funding["totalFunding"]
                    allpct = get_fraction_str(funding["progress"], 100)
                else:
                    allfund = None
                    allpct = None
                custom_location_code = plan.get("customLocationCode")
                if custom_location_code == "COVD":
                    continue

                countries = plan["countries"]
                countryid_iso3mapping = dict()
                has_ukr = False
                for country in countries:
                    countryiso = country["iso3"]
                    if countryiso:
                        if countryiso == "UKR":
                            has_ukr = True
                        countryid = country["id"]
                        countryid_iso3mapping[str(countryid)] = countryiso
                if not has_ukr:
                    continue
                if len(countryid_iso3mapping) == 1:
                    countryiso = countryid_iso3mapping.popitem()[1]
                    if not countryiso or countryiso not in self.countryiso3s:
                        continue
                    plan_type = plan["planType"]["name"].lower()
                    if plan_type == "humanitarian response plan":
                        if allreq:
                            hrp_requirements[countryiso] = allreq
                        else:
                            hrp_requirements[countryiso] = None
                        if allfund and allreq:
                            hrp_funding[countryiso] = allfund
                            hrp_percentage[countryiso] = allpct
                    else:
                        if plan_type == "regional response plan":
                            regional_plans[plan_name] = {
                                "requirements": allreq,
                                "funding": allfund,
                                "percentfunded": allpct,
                            }
                        if custom_location_code != "UKRN":
                            add_other_requirements_and_funding(
                                countryiso, plan_name, allreq, allfund, allpct
                            )
                else:
                    (
                        countryreqs,
                        countryfunds,
                    ) = self.get_requirements_and_funding_location(
                        base_url, plan, countryid_iso3mapping, downloader
                    )
                    regional_plans[plan_name] = {
                        "requirements": allreq,
                        "funding": allfund,
                        "percentfunded": allpct,
                    }
                    for countryiso in countryfunds:
                        countryfund = countryfunds[countryiso]
                        countryreq = countryreqs.get(countryiso)
                        if countryreq:
                            countrypct = get_fraction_str(countryfund, countryreq)
                        else:
                            countrypct = None
                        add_other_requirements_and_funding(
                            countryiso, plan_name, countryreq, countryfund, countrypct
                        )
                    for countryiso in countryreqs:
                        if countryiso in countryfunds:
                            continue
                        add_other_requirements_and_funding(
                            countryiso, plan_name, countryreqs[countryiso], None, None
                        )

            def create_output(vallist):
                strings = list()
                for val in vallist:
                    if val is None:
                        strings.append("")
                    else:
                        strings.append(str(val))
                return "|".join(strings)

            for countryiso in other_planname:
                other_planname[countryiso] = create_output(other_planname[countryiso])
                other_requirements[countryiso] = create_output(
                    other_requirements[countryiso]
                )
                other_funding[countryiso] = create_output(other_funding[countryiso])
                other_percentage[countryiso] = create_output(
                    other_percentage[countryiso]
                )
            regional_values = self.get_values("regional")
            regional_plan = list(regional_plans.values())[
                0
            ]  # There should only be one regional plan!
            regional_values[0]["value"] = regional_plan["requirements"]
            regional_values[1]["value"] = regional_plan["funding"]
            regional_values[2]["value"] = regional_plan["percentfunded"]
            self.datasetinfo["date"] = self.today
            logger.info("Processed FTS")

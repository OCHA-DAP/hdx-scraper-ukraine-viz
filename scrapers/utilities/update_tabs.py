import logging

from hdx.data.dataset import Dataset
from hdx.location.country import Country
from hdx.scraper.utilities import get_isodate_from_dataset_date

logger = logging.getLogger(__name__)


national_headers = (
    ("iso3", "countryname"),
    ("#country+code", "#country+name"),
)
subnational_headers = (
    ("iso3", "countryname", "adm1_pcode", "adm1_name"),
    ("#country+code", "#country+name", "#adm1+code", "#adm1+name"),
)
sources_headers = (
    ("Indicator", "Date", "Source", "Url"),
    ("#indicator+name", "#date", "#meta+source", "#meta+url"),
)


def update_tab(outputs, name, data):
    if not data:
        return
    logger.info(f"Updating tab: {name}")
    for output in outputs.values():
        output.update_tab(name, data)


def update_regional(runner, outputs):
    rows = runner.get_rows("regional", ("value",))
    update_tab(outputs, "regional", rows)


def update_national(runner, names, countries, outputs):
    name_fn = lambda adm: Country.get_country_name_from_iso3(adm)

    fns = (lambda adm: adm, name_fn)
    rows = runner.get_rows("national", countries, national_headers, fns, names=names)
    update_tab(outputs, "national", rows)


def update_subnational(runner, adminone, outputs):
    def get_country_name(adm):
        countryiso3 = adminone.pcode_to_iso3[adm]
        return Country.get_country_name_from_iso3(countryiso3)

    fns = (
        lambda adm: adminone.pcode_to_iso3[adm],
        get_country_name,
        lambda adm: adm,
        lambda adm: adminone.pcode_to_name[adm],
    )
    rows = runner.get_rows("subnational", adminone.pcodes, subnational_headers, fns)
    update_tab(outputs, "subnational", rows)


def update_sources(runner, configuration, today, outputs):
    sources = list()
    for sourceinfo in configuration["additional_sources"]:
        date = sourceinfo.get("date")
        if date is None:
            if sourceinfo.get("force_date_today", False):
                date = today.strftime("%Y-%m-%d")
        source = sourceinfo.get("source")
        source_url = sourceinfo.get("source_url")
        dataset_name = sourceinfo.get("dataset")
        if dataset_name:
            dataset = Dataset.read_from_hdx(dataset_name)
            if date is None:
                date = get_isodate_from_dataset_date(dataset, today=today)
            if source is None:
                source = dataset["dataset_source"]
            if source_url is None:
                source_url = dataset.get_hdx_url()
        sources.append((sourceinfo["indicator"], date, source, source_url))
    sources.extend(runner.get_sources())
    update_tab(outputs, "sources", list(sources_headers) + sources)

import logging

from hdx.location.adminone import AdminOne
from hdx.location.country import Country
from hdx.scraper.runner import Runner
from hdx.utilities.dateparse import parse_date

from .acled import ACLED
from .filecopier import FileCopier
from .fts import FTS
from .idps import IDPs
from .timeseries import TimeSeries
from .unhcr import UNHCR
from .utilities.update_tabs import (
    update_national,
    update_regional,
    update_sources,
    update_subnational,
)

logger = logging.getLogger(__name__)


def get_indicators(
    configuration,
    today,
    retriever,
    outputs,
    tabs,
    scrapers_to_run=None,
    basic_auths=dict(),
    other_auths=dict(),
    nofilecopy=False,
    countries_override=None,
    errors_on_exit=None,
    use_live=True,
):
    Country.countriesdata(
        use_live=use_live,
        country_name_overrides=configuration["country_name_overrides"],
        country_name_mappings=configuration["country_name_mappings"],
    )

    if countries_override:
        countries = countries_override
    else:
        countries = configuration["countries"]
    configuration["countries_fuzzy_try"] = countries
    downloader = retriever.downloader
    adminone = AdminOne(configuration)
    runner = Runner(
        countries,
        adminone,
        downloader,
        basic_auths,
        today,
        errors_on_exit=errors_on_exit,
        scrapers_to_run=scrapers_to_run,
    )
    start_date = parse_date(configuration["additional_sources"][0]["source_date"])
    if nofilecopy:
        prioritise_scrapers = list()
    else:
        filecopiers = FileCopier.get_scrapers(configuration["copyfiles"], today)
        prioritise_scrapers = runner.add_customs(filecopiers)
    configurable_scrapers = dict()
    for level in ("national", "subnational"):
        suffix = f"_{level}"
        configurable_scrapers[level] = runner.add_configurables(
            configuration[f"scraper{suffix}"], level, suffix=suffix
        )
    fts = FTS(configuration["fts"], today, countries, basic_auths)
    unhcr = UNHCR(configuration["unhcr"], today, outputs, countries, downloader)
    idps = IDPs(configuration["idps"], today, outputs, downloader)
    acled = ACLED(
        configuration["acled"], start_date, today, outputs, downloader, other_auths
    )
    runner.add_customs(
        (
            fts,
            unhcr,
            idps,
            acled,
        )
    )
    timeseries = TimeSeries.get_scrapers(
        configuration["timeseries"], today, outputs, downloader
    )
    runner.add_customs(timeseries)
    prioritise_scrapers.extend(
        [
            "population_national",
            "population_subnational",
            "population_regional",
        ]
    )
    runner.run(prioritise_scrapers=prioritise_scrapers)

    if "regional" in tabs:
        update_regional(runner, outputs)
    if "national" in tabs:
        national_names = configurable_scrapers["national"]
        national_names.insert(1, "idps")
        national_names.insert(1, "unhcr")
        national_names.insert(len(national_names) - 1, "fts")
        update_national(
            runner,
            national_names,
            countries,
            outputs,
        )
    if "subnational" in tabs:
        update_subnational(runner, adminone, outputs)

    adminone.output_matches()
    adminone.output_ignored()
    adminone.output_errors()

    if "sources" in tabs:
        update_sources(runner, configuration, outputs)
    return countries

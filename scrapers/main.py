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
    outputs,
    tabs,
    scrapers_to_run=None,
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
        primary_countries = countries_override
    else:
        primary_countries = configuration["primary_countries"]
    configuration["countries_fuzzy_try"] = primary_countries
    adminone = AdminOne(configuration)
    runner = Runner(
        primary_countries,
        adminone,
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
            configuration[f"primary{suffix}"], level, suffix=suffix
        )
    fts = FTS(configuration["fts"], today, primary_countries)
    unhcr = UNHCR(configuration["unhcr"], today, outputs, primary_countries)
    idps = IDPs(configuration["idps"], today, outputs)
    acled = ACLED(configuration["acled"], start_date, today, outputs, adminone)
    runner.add_customs(
        (
            fts,
            unhcr,
            idps,
            acled,
        )
    )
    timeseries = TimeSeries.get_scrapers(configuration["timeseries"], today, outputs)
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
            primary_countries,
            outputs,
        )
    if "subnational" in tabs:
        update_subnational(runner, adminone, outputs)

    adminone.output_matches()
    adminone.output_ignored()
    adminone.output_errors()

    secondary_countries = configuration["secondary_countries"]
    configuration["countries_fuzzy_try"] = secondary_countries

    secondary_runner = Runner(
        secondary_countries,
        adminone,
        today,
        errors_on_exit=errors_on_exit,
        scrapers_to_run=scrapers_to_run,
    )
    level = "national"
    suffix = f"_{level}"
    configurable_scrapers = secondary_runner.add_configurables(
        configuration[f"secondary{suffix}"], level, suffix=suffix
    )
    secondary_runner.run()

    if "secondary_national" in tabs:
        update_national(
            secondary_runner,
            configurable_scrapers,
            secondary_countries,
            outputs,
            tab="secondary_national",
        )

    if "sources" in tabs:
        update_sources(runner, secondary_runner, configuration, outputs)

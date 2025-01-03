import re
from datetime import datetime

import scrapy
from city_scrapers_core.constants import COMMISSION
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


class CaconjMetroHousingAuthoritySpider(CityScrapersSpider):
    name = "caconj_metro_housing_authority"
    agency = "Cincinnati Metro Housing Authority"
    timezone = "America/New_York"

    def start_requests(self):
        # generate start and endtime for api request
        current_date = datetime.now()
        start_date = current_date - relativedelta(months=6)
        end_date = current_date + relativedelta(months=6)
        start_int = start_date.strftime("%s")
        end_int = end_date.strftime("%s")
        # generate url with stand & end times
        url = "https://cintimha.com/wp-admin/admin-ajax.php?action=get_calendar_events"
        f"&noheader=true&start_date={start_int}&end_date={end_int}"
        "&show_expired=true&event_category_id=executive-office-1466450825"

        yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        """
        Parse API response from Executive Office cintimha.com calendar.
        """

        data = response.json()

        for item in data:
            meeting = Meeting(
                title=item["title"],
                description="",
                classification=COMMISSION,
                start=self._parse_start(item),
                end=self._parse_end(item),
                all_day=item["allDay"],
                time_notes="",
                location=self._parse_location(item),
                links=self._parse_links(item),
                source=self._parse_source(response),
            )

            meeting["status"] = self._get_status(meeting)
            meeting["id"] = self._get_id(meeting)

            yield meeting

    def _parse_start(self, item):
        """Parse start datetime as a naive datetime object."""
        start = item["start"]
        start_no_tz = parse(start, ignoretz=True)
        return start_no_tz

    def _parse_end(self, item):
        """Parse end datetime as a naive datetime object. Added by pipeline if None"""
        end = item["end"]
        end_no_tz = parse(end, ignoretz=True)
        return end_no_tz

    def _parse_location(self, item):
        """Parse or generate location."""
        location = {"name": "", "address": ""}
        text = item["description"]
        regex = r"(at)?.+\s(at|the)\s?(.+)\sbeginning"
        match = re.search(regex, text)
        if match:
            address = match.group(3)
            location["address"] = address
            if "1635 Western Avenue" in address:
                # set location name to boardroom if certain address found
                location["name"] = "CMHA Boardroom"
            else:
                # split string up between name and address
                # ex: West Union Square, 2942 Banning Road, Cincinnati, OH 45239
                # name: West Union Square
                # address: 2942 Banning Road, Cincinnati, OH 45239
                parts = address.split(", ")
                location["name"] = parts[0]
                location["address"] = ", ".join(parts[1:])
        return location

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"title": "Event Link", "href": item["url"]}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url

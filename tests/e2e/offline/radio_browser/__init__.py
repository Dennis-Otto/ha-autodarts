"""A stand-in for Home Assistant's Radio Browser that keeps the tests off the internet.

Onboarding sets up Radio Browser, which looks up its radio stations on the internet as
soon as it starts, before a test could remove it. compose.yaml mounts this folder as
custom_components/radio_browser, which takes the place of the built-in integration,
and its config flow turns the offer of onboarding down. So the Home Assistant of the
end-to-end tests, the demo and the screenshots has no Radio Browser and calls nothing
on the internet for it; scenario.py checks that no entry of it exists.
"""

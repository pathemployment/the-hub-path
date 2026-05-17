# Security Policy

theHUB @PATH is a static informational website for employment professionals. We take the security of this site seriously even though it doesn't process or store personal data.

## Supported versions

Only the current `main` branch is supported. The live site at https://kwestwoodpath.github.io/the-hub-path/ always reflects the latest commit.

## What's in scope

- The HTML, CSS, and JavaScript in this repository
- Public content served from this site (assets, embedded forms, links)
- Configuration files (e.g., site.webmanifest, sitemap.xml)

## What's out of scope

- Vulnerabilities in third-party services we link to or embed (Microsoft Forms, Calendly, the Firecrawl-pulled job sources). Please report those to the respective vendors.
- Issues in the broader pathemployment.com infrastructure (separate ownership).
- Social engineering or phishing targeting PATH staff (report to PATH IT directly).

## Reporting a vulnerability

If you believe you have found a security vulnerability in this site, please **do not open a public GitHub issue**. Instead:

1. Email **Kevin Westwood** at `kevin.westwood@pathemployment.com` with the subject line `theHUB Security Report`.
2. Include:
   - A clear description of the issue
   - Steps to reproduce
   - The URL or file affected
   - Your assessment of the impact

We aim to acknowledge reports within **3 business days** and provide a status update within **10 business days**. Once a fix is in place, we will credit you in the commit message or release notes if you wish.

## What we ask in return

- Give us a reasonable opportunity to investigate and remediate before any public disclosure.
- Do not access, modify, or destroy data that does not belong to you.
- Do not perform actions that could degrade service for other users (load testing, denial of service, etc.).

## Our practices

- All site content is static — no server-side code, databases, or user authentication on the Hub site itself.
- We do not collect personally identifying information through the site beyond what users voluntarily submit through clearly labelled external forms (Microsoft Forms hosted by Microsoft).
- Google Analytics is loaded only after explicit cookie consent, with IP anonymization enabled.
- Dependencies: this site has no JavaScript build process and no npm packages. Third-party assets are loaded from named CDNs (Google Fonts).

Thank you for helping keep theHUB safe.

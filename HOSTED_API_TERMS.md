# Hosted API Terms of Service

These are the service terms for calling the hosted API at `arena.rone.dev`.
They are separate from the source-code licence in [LICENSE](LICENSE), which
governs the code rather than the service.

Site-wide terms are at <https://rone.dev/terms>. Where this document is more
specific about the hosted API, it governs.

## Independence and non-affiliation

Rone Arena is an independent, community-maintained project. It is **not**
affiliated with, endorsed by, sponsored by, or operated by Shanghai Moonton
Technology Co., Ltd.

"Mobile Legends: Bang Bang", "MLBB", and all related names, marks, logos and
in-game assets are trademarks of their respective owners. They are used here
descriptively, to say what the data is about, and not as an identifier of this
project. The project was renamed from "MLBB Public Data API" in 2026 for exactly
that reason.

The service reads publicly accessible endpoints and re-serves the data in a
structured form. The underlying data belongs to its original publisher and all
rights remain with them.

## No warranty

Data is provided as-is, with no warranty of accuracy, completeness, timeliness
or availability. Verify anything consequential against the official source
before relying on it. The maintainer accepts no liability for decisions made on
the basis of this data.

## No service level

This is a free public endpoint. There is no uptime commitment.

- Endpoints may be rate limited, moved, or withdrawn.
- The service publishes two restricted states, and they mean different things.
  **Maintenance** means the work is here and there is nowhere else to send you.
  **High traffic** means this host is shedding load and names a failover host in
  the response body. If you retry on a 503, read `alternative_endpoint` rather
  than assuming a host.
- Handle a 503 properly and cache what you can. If your product cannot tolerate
  the endpoint being unavailable, talk to us before you depend on it.

## Deprecation

Endpoints are marked `deprecated` in the OpenAPI schema rather than removed
without notice. A deprecated endpoint still answers and receives no further
work. Read the schema if you want to know what is on the way out — that is what
the flag is for.

## Acceptable use

- Do not send traffic that degrades the service for others. Automated load that
  does may be blocked without notice.
- Do not use the service to build anything that violates the terms of the game
  it describes, or that targets or harasses individual players.
- Player-facing endpoints require the player's own authentication. Do not use
  them against accounts that are not yours.

## Attribution

Attribution is requested rather than contractually required: a visible credit to
Rone Arena, linking to <https://arena.rone.dev>, wherever you present data from
this service.

Unlike Sivitas API, this service does not currently return a machine-readable
credit line in its responses. If attribution should be mandatory, that credit
field goes into the responses first — asking people to reproduce a line the API
never gave them would be a term nobody could comply with reliably.

## Commercial use

Using the hosted endpoint commercially, beyond what the source licence and this
document already permit, is by arrangement — mostly so we know what load to
expect. Contact us.

## Takedown

If you represent the data source or hold a mark this project touches, and you
want something changed or removed, contact us and it will be actioned. You do
not need a lawyer to make the request and we will not require one to act on it.

Tell us what the material is, where it is, and what right you are relying on.
We answer within three business days and say what we did.

## Security

Report vulnerabilities to <founder@rone.dev>. Do not open a public issue for a
security problem. Scope, safe-harbour terms and what is out of scope are at
<https://rone.dev/security>.

## Contact

- Operator: PT RoneAI Teknologi Internasional (RoneAI), Boyolali Regency, Central Java, Indonesia
- Maintainer: ridwaanhall
- General and commercial enquiries: <hello@rone.dev>
- Security: <founder@rone.dev>
- Website: <https://rone.dev>

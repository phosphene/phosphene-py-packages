Feature: Reference verification QC gate

  Every reference in an article's Bibliography field is verified against
  authoritative bibliographic databases (Crossref, OpenAlex, Semantic
  Scholar, arXiv) before the article can be promoted from Draft to Article.
  The gate is pure-domain + ports + thin adapters: no network in unit tests,
  providers behind the LookupClient port.

  Policy: Upstream Code Adoption Policy (Ed Phil, 2026-10-26) — this is a
  rewrite of an externally-assessed tool (shocklab reference-verifier),
  built to standard verification specifications.

  # --- Scoring & verdicts -------------------------------------------------

  Scenario: DOI resolves and metadata matches
    Given a reference with DOI "10.3389/fpos.2020.568704"
    And the provider returns a record with matching title, author surname, and year
    Then the verdict is "verified"
    And the matched DOI equals the cited DOI

  Scenario: No DOI but strong title match
    Given a reference lacking an explicit DOI
    And a provider search returns a record with matching title and author surname
    Then the verdict is "verified-secondary"

  Scenario: DOI resolves but metadata disagrees
    Given a reference with DOI "10.1234/fake-doi"
    And the provider returns a record whose title differs from the citation
    Then the verdict is "metadata_mismatch"
    And the mismatch reasons name the differing fields

  Scenario: Nothing matches anywhere
    Given a reference whose title matches no provider record
    Then the verdict is "not_found"

  Scenario: Borderline match stays unconfirmed
    Given a reference whose best candidate scores between the low and high thresholds
    Then the verdict is "low_confidence"

  Scenario: Same work cited under two entries
    Given a bibliography containing the same title cited twice
    Then the duplicate detector flags both entries

  # --- Gate semantics & Publication Decisions ----------------------------

  Scenario: metadata_mismatch blocks publish
    Given a bibliography with one metadata_mismatch verdict
    Then the gate decision is "block"

  Scenario: low_confidence warns while permitting review
    Given a bibliography with only low_confidence verdicts
    Then the gate decision is "warn"

  Scenario: all verified passes
    Given a bibliography where every reference verifies
    Then the gate decision is "pass"

  # --- Wikitext adapter ---------------------------------------------------

  Scenario: Our Bibliography field parses into references
    Given a wikitext bibliography with author-year entries and inline URLs
    When the wikitext adapter parses it
    Then each entry yields a Reference with text, year, and DOI extracted where present
    And wiki markup is stripped from the reference text

# Shutoff and generator draft review

The English START shutoff section now draws on the full Ready.gov Safety Skills
page (last updated March 20, 2026), the pinned FEMA Are You Ready guide, CDC's
generator and carbon monoxide guidance, CPSC publication 5123/102021, and CPSC's
May 27, 2026 post-storm safety notice. The source URLs are in
`content/sources.yaml`. Source retrieval is evidence for drafting, not named
human approval. No external publication or image is committed here.

The draft covers evacuation on suspected gas leaks, professional gas
restoration, household versus street water valves, individual circuits before
the main breaker, outdoor generator placement, dry operation, extension cords,
refueling, fuel storage, CO alarms and the initial response to possible
poisoning. Actions appear as separate list items in phone and print editions.
The Spanish text remains an unreviewed machine translation bound to the exact
English body hash. Both editions retain their review markers.

Required reviews remain explicit in the content:

- Utility safety: outside gas-valve identification and safe access, and safe
  household water-valve operation. Ready.gov notes that gas installations have
  different procedures. A universal quarter-turn instruction is not established;
  the gas tag's wording also needs this review.
- Electrical safety: panel identification and conditions that prohibit approach
  or operation, including wet or damaged equipment and solar, battery or
  generator supplies. Turning off the main does not establish that a panel is
  safe to open or service.
- Generator and clinical safety: placement, cords and loads, fuel handling,
  poisoning response and the no-response/re-entry branch. The newer CPSC notice
  says to leave a suspected gas leak immediately without operating electronics;
  the draft follows that evacuation wording. Ready.gov also discusses opening
  a window and an outside shutoff; the final sequence still requires review.

Render both editions with `ck core --languages en es --epoch 1793404800
--output build/review/core` in the pinned container. Check headings and contents
links, separate actions, citations, readable phone layout, draft warnings and the
Spanish footer. Physical-device checks and release-epoch regeneration remain
open. The agent does not set either edition to reviewed.

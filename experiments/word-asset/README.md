# Shared Word XML asset and complete translation rehearsal

This extends the frozen `2026-09-21-word-short-tables` prototype. It does not
edit the English checkout, real translation tree, pipeline lock or version.

## Two distinct proofs

1. `asset_recipe.py` moves the exact machine XML bytes from `.xml.j2` template
   text to an `.xml` asset and updates only the two Word `enrich-docx` paths.
   `asset_trial.py` verifies the pinned local worker before packaging.
   `asset_native.py` checks twelve actual DSW pairs: identical HTML, identical
   PDF and LibreOffice preview pixels/geometry, and every Word ZIP component
   identical except validated timestamps. No downloaded Word file is patched.
2. `source_rehearsal.py` starts from the complete locked English source and
   carries forward five prior prototype Jinja changes plus the two shared Word
   helpers. It uses the existing layout preparation, translation expansion,
   export and merge, without modifying the real translation tree.
   `source_finish.py` reviews bounded translation additions, syncs the full
   Chinese source, audits structure and uses actual TDK verify/package commands.
   `source_parity.py` compares both packaged sources against the frozen native
   prototype over 3,312 case/layout/mode/escaping combinations.

The second proof is **not a native render of the rebuilt full-source packages**.
Keep that acceptance boundary explicit; native asset loading and rebuilt-source
structural parity must not be misrepresented as paired-version release QA.

## Translation-compatible source shape

The unadapted full-source trial has 102 Chinese parity failures, retained in the
archive. It is not acceptable even though TDK verification succeeds:

- The existing translator recognizes named `*Sentences|join(' ')` expressions,
  not sliced expressions. Q9 now assigns the two slices to named lists before
  joining them. English output is unchanged; Chinese gets its existing joining
  rule, without editing generated Chinese or arbitrary user answers.
- In Q15, preserve the whole existing name/number paragraph in the review/named
  branch, and expose the submission's neutral `Project` label as one complete
  translator-facing paragraph. Wrapping only the missing-name expression had
  changed the old translation boundary and introduced trailing whitespace.

Both adaptations reverse exactly to the native English prototype. The final
translation rehearsal retains all 762 reviewed source/target pairs and adds
five, including the dedicated budget-label sentence. Five duplicate existing
units could not migrate automatically; they are restored only after proving
that every old copy has the same target text. No fuzzy translation migration.

## Reproduction and next integration

Use the locked tooling virtualenv. Native fixtures use **base case names** with
`run_missing_info.py --cases ethics-missing ethics-answered ethics-long
--profiles review submission`; Word preview names include the profile suffix.
Generate all native files before previews. Only use the owned localhost pilot,
preserve failed receipts, clean only its two test templates, restore capacity
and stock worker, and stop the four owned services afterward.

For complete source rehearsal, select a new output path:

```sh
../dsw-document-template-tool/.venv/bin/python experiments/word-asset/source_rehearsal.py \
  --english ../science-europe-template --tooling ../dsw-document-template-tool \
  --adapt-prose --output outputs/REPLACE_WITH_NEW_DIRECTORY
../dsw-document-template-tool/.venv/bin/python experiments/word-asset/source_finish.py \
  --english ../science-europe-template --tooling ../dsw-document-template-tool \
  --output outputs/REPLACE_WITH_NEW_DIRECTORY
```

Next integrate the seven files and bounded Word metadata changes into the
English repository, add an exact historical projection (do not relax older
gates), rebuild the Chinese translation tree with this reviewed delta, pin the
new full English SHA and pair versions. Then render the actual rebuilt packages
and compare them with the native prototype. Keep working on the existing topic
branch; do not create permanent language/profile branches or a second Chinese
Word implementation. No production deployment or full compliance claim here.

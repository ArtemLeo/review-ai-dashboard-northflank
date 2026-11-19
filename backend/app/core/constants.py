"""Shared constants that must not depend on any application package.

This module deliberately imports nothing from the project.  It is the safe
home for values that are needed by more than one layer — in particular the
language-code limit, which is shared between the Pydantic schemas and the AI
parsing helpers.  Keeping it here means the schema layer never has to reach
into the AI layer, which is what used to close an import cycle between
:mod:`app.schemas` and :mod:`app.ai`.
"""

#: Longest language code the database column can store.
#:
#: The value is shared by the API schemas (which validate incoming language
#: codes) and by the AI parsing helpers (which normalise the codes returned by
#: a model), so both layers must agree on it exactly.
MAX_LANGUAGE_CODE_LENGTH: int = 10

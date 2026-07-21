# LayoutLab Feature Concepts

> Feature Concepts describe a complete product capability before it is split into
> binding Design Decisions and implementation work packages.

------------------------------------------------------------------------

## Why this folder exists

LayoutLab previously had two documentation levels:

- `Future_Ideas.md` for broad, early product ideas
- Design Decisions for accepted architectural choices

Large features often need a stable description between those levels. A Feature
Concept captures the complete user experience, domain behaviour, invariants and
open architectural questions without prematurely fixing every API or module.

This enables roadmap items, implementation tickets and later DDs to reference one
authoritative concept instead of copying fragments of it.

------------------------------------------------------------------------

## Lifecycle

```text
Future Idea
    -> Feature Concept (FC-xxx)
    -> one or more Design Decisions
    -> roadmap work packages / tickets
    -> implementation
    -> as-built contracts and user documentation
```

A Feature Concept is **not** a binding protocol specification. If implementation
requires a significant architectural choice, create or amend a DD first. Binding
field names and commands belong in the appropriate contract documents.

------------------------------------------------------------------------

## Status values

| Status | Meaning |
|---|---|
| **Draft** | Still being discussed; not ready to schedule |
| **Ready for decomposition** | Product behaviour is coherent; DDs and work packages may be derived |
| **Active** | At least one referenced work package is in progress |
| **Implemented** | The concept's agreed MVP is shipped; as-built docs are authoritative |
| **Superseded** | Replaced by another concept or product decision |

------------------------------------------------------------------------

## Index

| ID | Concept | Status | Related architecture |
|---|---|---|---|
| [FC-001](FC-001-semantic-direct-manipulation-and-multi-room-editing.md) | Semantic Direct Manipulation and Multi-Room Editing | **Ready for decomposition** | DD-009, DD-010, DD-014; new DDs required before implementation |

------------------------------------------------------------------------

## Referencing rules

- Roadmap items use a stable identifier such as `FC-001/WP-02`.
- DDs link back to the Feature Concept whose product behaviour they formalize.
- The Feature Concept links to resulting DDs and work packages as they are created.
- Do not duplicate the full concept in `Future_Ideas.md`, a DD or a ticket.
- When implementation ships, update the relevant as-built contracts; the concept
  remains the product rationale and behaviour overview.


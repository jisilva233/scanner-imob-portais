---
task: Deduplicar Listings
responsavel: "@data-agent"
elicit: false
atomic_layer: task
Entrada:
  - session: SQLAlchemy Session (opcional — usa engine padrão se não fornecido)
Saida:
  - removed: Número de duplicatas removidas/desativadas
---

# Task: Deduplicate Listings

## Propósito
Detectar e desativar anúncios duplicados que escaparam da deduplicação por fingerprint.
Duplicatas são detectadas por URL idêntica (casos onde preço pode ter mudado).

## Implementação

```python
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from db.models import PropertyListingDB, engine


def deduplicate_by_url() -> int:
    """
    Desativa entradas duplicadas mantendo apenas a mais recente por URL.

    Returns:
        Número de registros desativados
    """
    deactivated = 0

    with Session(engine) as session:
        # Encontrar URLs com múltiplos registros ativos
        subq = (
            select(
                PropertyListingDB.listing_url,
                func.count(PropertyListingDB.id).label("cnt"),
            )
            .where(PropertyListingDB.is_active == True)
            .group_by(PropertyListingDB.listing_url)
            .having(func.count(PropertyListingDB.id) > 1)
            .subquery()
        )

        duplicated_urls = session.execute(
            select(subq.c.listing_url)
        ).scalars().all()

        for url in duplicated_urls:
            # Manter o mais recente, desativar os demais
            records = (
                session.execute(
                    select(PropertyListingDB)
                    .where(
                        PropertyListingDB.listing_url == url,
                        PropertyListingDB.is_active == True,
                    )
                    .order_by(PropertyListingDB.created_at.desc())
                )
                .scalars()
                .all()
            )

            # Desativar todos exceto o primeiro (mais recente)
            for record in records[1:]:
                record.is_active = False
                deactivated += 1

        session.commit()

    print(f"[DEDUP] Desativados {deactivated} registros duplicados")
    return deactivated
```

package com.pompomhills.intelligence.character;

import com.pompomhills.intelligence.common.domain.AuditableEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.UUID;

@Entity
@Table(name = "characters")
public class CharacterEntity extends AuditableEntity {
  @Id private UUID id;

  @Column(nullable = false, unique = true)
  private String name;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private CharacterStatus status;

  private String notes;

  @Column(nullable = false)
  private boolean active;

  protected CharacterEntity() {}

  public CharacterEntity(UUID id, String name, CharacterStatus status, String notes) {
    this.id = id;
    this.name = name;
    this.status = status;
    this.notes = notes;
    this.active = true;
  }

  public UUID getId() {
    return id;
  }

  public String getName() {
    return name;
  }

  public CharacterStatus getStatus() {
    return status;
  }

  public String getNotes() {
    return notes;
  }

  public boolean isActive() {
    return active;
  }
}

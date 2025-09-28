package ru.spbu.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import ru.spbu.entity.MapEntity;

@Repository
public interface MapRepository extends JpaRepository<MapEntity, Long> {
}
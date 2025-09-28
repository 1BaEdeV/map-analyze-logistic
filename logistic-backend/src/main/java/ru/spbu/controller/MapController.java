package ru.spbu.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import ru.spbu.service.MapService;

@RestController
@RequestMapping("/api/maps")
@RequiredArgsConstructor
public class MapController {
  private final MapService mapService;

  @PostMapping("/upload")
  public ResponseEntity<String> uploadMap(@RequestParam("file") MultipartFile file) {
    try {
      mapService.saveMap(file);
      return ResponseEntity.ok("Карта успешно загружена!");
    } catch (Exception e) {
      return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
          .body("Ошибка загрузки карты: " + e.getMessage());
    }
  }
}

package ru.spbu.service;

import java.io.IOException;
import java.time.LocalDateTime;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import ru.spbu.entity.MapEntity;
import ru.spbu.repository.MapRepository;

@Service
@RequiredArgsConstructor
public class MapService {

  private final MapRepository mapRepository;

  public void saveMap(MultipartFile file) throws IOException {
    MapEntity entity = new MapEntity();
    entity.setFileName(file.getOriginalFilename());
    entity.setContentType(file.getContentType());
    entity.setData(file.getBytes());
    entity.setUploadDate(LocalDateTime.now());

    mapRepository.save(entity);
  }
}

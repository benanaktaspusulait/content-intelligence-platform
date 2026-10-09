package com.pompom.creative.config;

import java.sql.SQLException;
import org.flywaydb.core.api.callback.Callback;
import org.flywaydb.core.api.callback.Context;
import org.flywaydb.core.api.callback.Event;
import org.springframework.stereotype.Component;

/** Keeps render objects in their schema while locating an existing pgcrypto extension. */
@Component
public class RenderMigrationSearchPath implements Callback {
  @Override
  public boolean supports(Event event, Context context) {
    return event == Event.BEFORE_EACH_MIGRATE;
  }

  @Override
  public boolean canHandleInTransaction(Event event, Context context) {
    return true;
  }

  @Override
  public void handle(Event event, Context context) {
    try (var statement = context.getConnection().createStatement()) {
      String extensionSchema = "public";
      try (var result = statement.executeQuery(
          "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='pgcrypto'")) {
        if (result.next()) extensionSchema = result.getString(1);
      }
      // Extension location comes from PostgreSQL metadata; quote the identifier nevertheless.
      statement.execute("SET LOCAL search_path = creative_render, \""
          + extensionSchema.replace("\"", "\"\"") + "\", public");
    } catch (SQLException error) {
      throw new IllegalStateException("Render migration extension search path unavailable", error);
    }
  }

  @Override
  public String getCallbackName() {
    return "render-extension-search-path";
  }
}

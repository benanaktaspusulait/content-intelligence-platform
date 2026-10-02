package com.pompom.creative.migration;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.flywaydb.core.Flyway;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Shared helpers for the creative_render Flyway migration tests. These tests exercise the real
 * migrations against a disposable PostgreSQL container, replicating the production Flyway schema
 * ownership (independent history living in {@code creative_render}).
 */
final class RenderMigrationSupport {

  static final String IMAGE = "postgres:17-alpine";
  static final String SCHEMA = "creative_render";
  static final String LOCATION = "classpath:db/migration";

  private RenderMigrationSupport() {}

  static PostgreSQLContainer<?> newContainer() {
    return new PostgreSQLContainer<>(IMAGE)
        .withDatabaseName("creative_render_test")
        .withUsername("render")
        .withPassword("render_test");
  }

  /** Runs the render service migrations with the same schema ownership used in production. */
  static void migrate(PostgreSQLContainer<?> db) {
    Flyway.configure()
        .dataSource(db.getJdbcUrl(), db.getUsername(), db.getPassword())
        .schemas(SCHEMA)
        .defaultSchema(SCHEMA)
        .createSchemas(true)
        .locations(LOCATION)
        .load()
        .migrate();
  }

  static Connection connect(PostgreSQLContainer<?> db) throws Exception {
    return DriverManager.getConnection(db.getJdbcUrl(), db.getUsername(), db.getPassword());
  }

  static Set<String> tableNames(PostgreSQLContainer<?> db, String schema) {
    Set<String> names = new LinkedHashSet<>();
    try (Connection c = connect(db);
        Statement st = c.createStatement()) {
      try (ResultSet rs =
          st.executeQuery(
              "SELECT table_name FROM information_schema.tables WHERE table_schema = '"
                  + schema
                  + "'")) {
        while (rs.next()) {
          names.add(rs.getString(1));
        }
      }
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
    return names;
  }

  /**
   * Returns a human readable description of every foreign key declared on a table in {@code schema}
   * that references a table living in a different schema (e.g. a leak from creative_render into
   * public).
   */
  static List<String> crossSchemaForeignKeys(PostgreSQLContainer<?> db, String schema) {
    List<String> violations = new ArrayList<>();
    String sql =
        "SELECT con.conname, child_ns.nspname AS child_schema, child.relname AS child_table,"
            + " parent_ns.nspname AS parent_schema, parent.relname AS parent_table "
            + "FROM pg_constraint con "
            + "JOIN pg_class child ON child.oid = con.conrelid "
            + "JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace "
            + "JOIN pg_class parent ON parent.oid = con.confrelid "
            + "JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace "
            + "WHERE con.contype = 'f' AND child_ns.nspname = '"
            + schema
            + "' AND parent_ns.nspname <> '"
            + schema
            + "'";
    try (Connection c = connect(db);
        Statement st = c.createStatement();
        ResultSet rs = st.executeQuery(sql)) {
      while (rs.next()) {
        violations.add(
            rs.getString("child_schema")
                + "."
                + rs.getString("child_table")
                + " -> "
                + rs.getString("parent_schema")
                + "."
                + rs.getString("parent_table")
                + " ("
                + rs.getString("conname")
                + ")");
      }
    } catch (Exception e) {
      throw new RuntimeException(e);
    }
    return violations;
  }

  static long count(Connection c, String qualifiedTable) throws Exception {
    try (Statement st = c.createStatement();
        ResultSet rs = st.executeQuery("SELECT count(*) FROM " + qualifiedTable)) {
      rs.next();
      return rs.getLong(1);
    }
  }

  static String scalarString(Connection c, String sql) throws Exception {
    try (Statement st = c.createStatement();
        ResultSet rs = st.executeQuery(sql)) {
      rs.next();
      return rs.getString(1);
    }
  }

  static Map<String, Long> statusDistribution(Connection c, String qualifiedTable)
      throws Exception {
    Map<String, Long> dist = new LinkedHashMap<>();
    try (Statement st = c.createStatement();
        ResultSet rs =
            st.executeQuery(
                "SELECT status, count(*) FROM " + qualifiedTable + " GROUP BY status")) {
      while (rs.next()) {
        dist.put(rs.getString(1), rs.getLong(2));
      }
    }
    return dist;
  }

  static Set<String> idSet(Connection c, String qualifiedTable) throws Exception {
    Set<String> ids = new LinkedHashSet<>();
    try (Statement st = c.createStatement();
        ResultSet rs = st.executeQuery("SELECT id::text FROM " + qualifiedTable)) {
      while (rs.next()) {
        ids.add(rs.getString(1));
      }
    }
    return ids;
  }

  /** Executes a multi-statement SQL script read from the test classpath. */
  static void execClasspathScript(Connection c, String resourcePath) throws Exception {
    String sql = readClasspath(resourcePath);
    try (Statement st = c.createStatement()) {
      st.execute("SET search_path TO creative_render, public, pg_catalog");
      st.execute(sql);
    }
  }

  static String readClasspath(String resourcePath) throws Exception {
    try (InputStream in = RenderMigrationSupport.class.getResourceAsStream(resourcePath)) {
      if (in == null) {
        throw new IllegalStateException("Resource not found on classpath: " + resourcePath);
      }
      return new String(in.readAllBytes(), StandardCharsets.UTF_8);
    }
  }
}

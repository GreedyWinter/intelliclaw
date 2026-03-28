import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models.dart';

class IntelliclawApi {
  IntelliclawApi({http.Client? client})
      : _client = client ?? http.Client();

  static const String defaultBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );

  final http.Client _client;

  Uri _uri(String path) => Uri.parse('$defaultBaseUrl$path');

  Future<bool> healthCheck() async {
    final response = await _client.get(_uri('/health'));
    _ensureSuccess(response);
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return data['status'] == 'ok';
  }

  Future<ProjectSummary> fetchSummary() async {
    final response = await _client.get(_uri('/projects/summary'));
    _ensureSuccess(response);
    return ProjectSummary.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<List<Project>> fetchProjects() async {
    final response = await _client.get(_uri('/projects'));
    _ensureSuccess(response);
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => Project.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Project> createProject(String name) async {
    final response = await _client.post(
      _uri('/projects'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'name': name}),
    );
    _ensureSuccess(response);
    return Project.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<ProjectDetail> fetchProjectDetail(int projectId) async {
    final response = await _client.get(_uri('/projects/$projectId'));
    _ensureSuccess(response);
    return ProjectDetail.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<ProjectDocument> uploadDocument({
    required int projectId,
    required String filename,
    required List<int> bytes,
    String? contentType,
  }) async {
    final request = http.MultipartRequest(
      'POST',
      _uri('/projects/$projectId/documents'),
    );
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: filename,
      ),
    );

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    _ensureSuccess(response);
    return ProjectDocument.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<AnalysisRun> createAnalysisRun({
    required int projectId,
    String? prompt,
  }) async {
    final response = await _client.post(
      _uri('/projects/$projectId/analysis-runs'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'prompt': prompt ??
            'Analyze uploaded competitor PDFs for feature gaps and produce a comparison summary plus output artifacts.',
      }),
    );
    _ensureSuccess(response);
    return AnalysisRun.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  void _ensureSuccess(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return;
    }

    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final detail = data['detail'] ?? data['error'];
      throw IntelliclawApiException(detail?.toString() ?? 'Request failed.');
    } catch (_) {
      throw IntelliclawApiException('Request failed: ${response.statusCode}.');
    }
  }
}

class IntelliclawApiException implements Exception {
  const IntelliclawApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class Project {
  const Project({
    required this.id,
    required this.name,
    required this.createdAt,
    required this.documentCount,
  });

  final int id;
  final String name;
  final String createdAt;
  final int documentCount;

  factory Project.fromJson(Map<String, dynamic> json) {
    return Project(
      id: json['id'] as int,
      name: json['name'] as String,
      createdAt: json['created_at'] as String? ?? '',
      documentCount: json['document_count'] as int? ?? 0,
    );
  }
}

class ProjectSummary {
  const ProjectSummary({
    required this.projectCount,
    required this.documentCount,
  });

  final int projectCount;
  final int documentCount;

  factory ProjectSummary.fromJson(Map<String, dynamic> json) {
    return ProjectSummary(
      projectCount: json['project_count'] as int? ?? 0,
      documentCount: json['document_count'] as int? ?? 0,
    );
  }
}

class ProjectDocument {
  const ProjectDocument({
    required this.id,
    required this.projectId,
    required this.filename,
    required this.filePath,
    required this.contentType,
    required this.sizeBytes,
    required this.status,
    required this.createdAt,
  });

  final int id;
  final int projectId;
  final String filename;
  final String? filePath;
  final String? contentType;
  final int? sizeBytes;
  final String status;
  final String createdAt;

  factory ProjectDocument.fromJson(Map<String, dynamic> json) {
    return ProjectDocument(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      filename: json['filename'] as String,
      filePath: json['file_path'] as String?,
      contentType: json['content_type'] as String?,
      sizeBytes: json['size_bytes'] as int?,
      status: json['status'] as String? ?? 'uploaded',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class AnalysisRun {
  const AnalysisRun({
    required this.id,
    required this.projectId,
    required this.status,
    required this.pipelineVersion,
    required this.summary,
    required this.resultPath,
    required this.errorMessage,
    required this.stepResults,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final int projectId;
  final String status;
  final String pipelineVersion;
  final String? summary;
  final String? resultPath;
  final String? errorMessage;
  final List<AnalysisStep> stepResults;
  final String createdAt;
  final String updatedAt;

  factory AnalysisRun.fromJson(Map<String, dynamic> json) {
    final steps = (json['step_results'] as List<dynamic>? ?? const [])
        .map((item) => AnalysisStep.fromJson(item as Map<String, dynamic>))
        .toList();

    return AnalysisRun(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      status: json['status'] as String? ?? 'pending',
      pipelineVersion: json['pipeline_version'] as String? ?? 'v1',
      summary: json['summary'] as String?,
      resultPath: json['result_path'] as String?,
      errorMessage: json['error_message'] as String?,
      stepResults: steps,
      createdAt: json['created_at'] as String? ?? '',
      updatedAt: json['updated_at'] as String? ?? '',
    );
  }
}

class AnalysisStep {
  const AnalysisStep({
    required this.name,
    required this.status,
    required this.details,
  });

  final String name;
  final String status;
  final Map<String, dynamic> details;

  factory AnalysisStep.fromJson(Map<String, dynamic> json) {
    return AnalysisStep(
      name: json['name'] as String? ?? '',
      status: json['status'] as String? ?? '',
      details: (json['details'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

class ProjectDetail {
  const ProjectDetail({
    required this.project,
    required this.documents,
    required this.analysisRuns,
  });

  final Project project;
  final List<ProjectDocument> documents;
  final List<AnalysisRun> analysisRuns;

  factory ProjectDetail.fromJson(Map<String, dynamic> json) {
    return ProjectDetail(
      project: Project.fromJson(json),
      documents: (json['documents'] as List<dynamic>? ?? const [])
          .map((item) => ProjectDocument.fromJson(item as Map<String, dynamic>))
          .toList(),
      analysisRuns: (json['analysis_runs'] as List<dynamic>? ?? const [])
          .map((item) => AnalysisRun.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

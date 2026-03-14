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

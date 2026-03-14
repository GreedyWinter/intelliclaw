import 'package:flutter/material.dart';

import 'api/intelliclaw_api.dart';
import 'dashboard_page.dart';

class IntelliclawApp extends StatelessWidget {
  const IntelliclawApp({super.key, this.api});

  final IntelliclawApi? api;

  @override
  Widget build(BuildContext context) {
    const seedColor = Color(0xFF0B5FFF);

    return MaterialApp(
      title: 'Intelliclaw',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seedColor),
        scaffoldBackgroundColor: const Color(0xFFF4F7FB),
        useMaterial3: true,
        fontFamily: 'Georgia',
      ),
      home: DashboardPage(api: api),
    );
  }
}

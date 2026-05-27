// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// EoSim iOS API Client — connects to https://api.eosim.io

import Foundation
import CoreLocation

/// Production API client for EoSim iOS app.
/// All requests go to https://api.eosim.io — never localhost.
final class EoSimAPIClient {

    // MARK: - Production Endpoints
    static let apiBase = "https://api.eosim.io"
    static let wsBase = "wss://api.eosim.io"
    static let docsURL = "https://docs.eosim.io"
    static let statusURL = "https://status.eosim.io"
    static let appURL = "https://app.eosim.io"

    static let shared = EoSimAPIClient()

    private let session: URLSession
    private var apiKey: String?

    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        config.httpAdditionalHeaders = [
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Client": "EoSim-iOS/3.0.1",
            "X-Platform": "ios",
        ]
        self.session = URLSession(configuration: config)
    }

    func setAPIKey(_ key: String) {
        self.apiKey = key
    }

    // MARK: - Health Check
    func health() async throws -> HealthResponse {
        try await get("/api/v1/health")
    }

    // MARK: - Platforms
    func listPlatforms() async throws -> PlatformsResponse {
        try await get("/api/v1/platforms")
    }

    // MARK: - Simulations
    func listSimulations() async throws -> SimulationsResponse {
        try await get("/api/v1/simulations")
    }

    func createSimulation(name: String, type: String, config: [String: Any] = [:]) async throws -> SimulationResponse {
        let body: [String: Any] = ["name": name, "type": type, "config": config]
        return try await post("/api/v1/simulations", body: body)
    }

    func startSimulation(id: String) async throws -> SimulationResponse {
        try await post("/api/v1/simulations/\(id)/start", body: [:])
    }

    func stopSimulation(id: String) async throws -> SimulationResponse {
        try await post("/api/v1/simulations/\(id)/stop", body: [:])
    }

    // MARK: - Modules
    func listModules() async throws -> ModulesResponse {
        try await get("/api/v1/modules")
    }

    // MARK: - Location-aware region selection
    func selectRegion(for location: CLLocation) -> String {
        let lon = location.coordinate.longitude
        if lon > -30 && lon < 60 { return "https://eu.api.eosim.io" }
        if lon >= 60 { return "https://ap.api.eosim.io" }
        return "https://api.eosim.io"
    }

    // MARK: - Private helpers
    private func get<T: Decodable>(_ path: String) async throws -> T {
        let url = URL(string: Self.apiBase + path)!
        var request = URLRequest(url: url)
        if let key = apiKey { request.setValue(key, forHTTPHeaderField: "X-API-Key") }
        let (data, _) = try await session.data(for: request)
        return try JSONDecoder().decode(T.self, from: data)
    }

    private func post<T: Decodable>(_ path: String, body: [String: Any]) async throws -> T {
        let url = URL(string: Self.apiBase + path)!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        if let key = apiKey { request.setValue(key, forHTTPHeaderField: "X-API-Key") }
        let (data, _) = try await session.data(for: request)
        return try JSONDecoder().decode(T.self, from: data)
    }
}

// MARK: - Response Models
struct HealthResponse: Decodable {
    let status: String
    let version: String
    let platform: String
    let uptime: Double
}

struct PlatformsResponse: Decodable {
    let platforms: [String]
}

struct SimulationsResponse: Decodable {
    let simulations: [SimulationInfo]
}

struct SimulationResponse: Decodable {
    let simulation: SimulationInfo
}

struct SimulationInfo: Decodable, Identifiable {
    let id: String
    let name: String
    let type: String
    let status: String
    let createdAt: String?
}

struct ModulesResponse: Decodable {
    let modules: [ModuleInfo]
    let count: Int
}

struct ModuleInfo: Decodable, Identifiable {
    var id: String { type }
    let type: String
    let name: String
    let description: String
    let version: String
}

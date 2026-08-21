from __future__ import annotations

import ast
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CompiledSignal:
    expression: str
    tree: ast.Expression


class StrategyDSL:
    @staticmethod
    def compile(expression: str, fields: set[str]) -> CompiledSignal:
        if len(expression) > 512:
            raise ValueError("策略表达式过长")
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as error:
            raise ValueError("策略表达式语法无效") from error
        allowed = (ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Name, ast.Load, ast.Constant, ast.And, ast.Or, ast.Not, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Gt, ast.GtE, ast.Lt, ast.LtE, ast.Eq, ast.NotEq, ast.USub)
        for node in ast.walk(tree):
            if not isinstance(node, allowed):
                raise ValueError("策略表达式包含不允许的操作")
            if isinstance(node, ast.Name) and node.id not in fields:
                raise ValueError(f"字段未在白名单: {node.id}")
        return CompiledSignal(expression=expression, tree=tree)
